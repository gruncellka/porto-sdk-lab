import { createWriteStream } from "node:fs";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import { dirname } from "node:path";
import { Readable } from "node:stream";
import { pipeline } from "node:stream/promises";

function readUint32LE(data: Uint8Array, offset: number): number {
    return (
        data[offset] |
        (data[offset + 1] << 8) |
        (data[offset + 2] << 16) |
        (data[offset + 3] << 24)
    ) >>> 0;
}

function readUint16LE(data: Uint8Array, offset: number): number {
    return data[offset] | (data[offset + 1] << 8);
}

/** DHL document links often return a store-method ZIP with a single 0.png entry. */
/** Stamp dimension calibration: use Python `labs.lib.python.mark_measure` (SoT). */
export function normalizeStampBytes(data: Uint8Array): Uint8Array {
    if (
        data.length >= 8 &&
        data[0] === 0x89 &&
        data[1] === 0x50 &&
        data[2] === 0x4e &&
        data[3] === 0x47
    ) {
        return data;
    }
    if (data.length >= 4 && data[0] === 0x50 && data[1] === 0x4b) {
        for (let offset = 0; offset < data.length - 30; offset += 1) {
            if (
                data[offset] !== 0x50 ||
                data[offset + 1] !== 0x4b ||
                data[offset + 2] !== 0x03 ||
                data[offset + 3] !== 0x04
            ) {
                continue;
            }
            const compression = readUint16LE(data, offset + 8);
            const compressedSize = readUint32LE(data, offset + 18);
            const nameLength = readUint16LE(data, offset + 26);
            const extraLength = readUint16LE(data, offset + 28);
            const nameStart = offset + 30;
            const name = new TextDecoder().decode(
                data.subarray(nameStart, nameStart + nameLength),
            );
            const dataStart = nameStart + nameLength + extraLength;
            if (compression !== 0 || !name.toLowerCase().endsWith(".png")) {
                continue;
            }
            return data.subarray(dataStart, dataStart + compressedSize);
        }
        throw new Error("Internetmarke stamp ZIP contains no PNG entry");
    }
    throw new Error(`Unsupported Internetmarke stamp payload (len=${data.length})`);
}

export async function downloadStampPng(url: string): Promise<Uint8Array> {
    const response = await fetch(url);
    if (!response.ok) {
        throw new Error(`Stamp download failed: ${response.status}`);
    }
    return normalizeStampBytes(new Uint8Array(await response.arrayBuffer()));
}

export async function saveStampPng(url: string, path: string): Promise<void> {
    const png = await downloadStampPng(url);
    await mkdir(dirname(path), { recursive: true });
    await pipeline(Readable.from(Buffer.from(png)), createWriteStream(path));
}

export async function repairStampPngFile(path: string): Promise<boolean> {
    const raw = new Uint8Array(await readFile(path));
    try {
        const png = normalizeStampBytes(raw);
        if (png.length === raw.length && png.every((byte, index) => byte === raw[index])) {
            return true;
        }
        await writeFile(path, png);
        return true;
    } catch {
        return false;
    }
}
