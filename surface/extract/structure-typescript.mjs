#!/usr/bin/env node
/**
 * Full TypeScript package structure extract (declarations only).
 * Usage: node structure-typescript.mjs <srcRoot> [typescriptPkgRoot]
 */

import fs from "node:fs";
import path from "node:path";
import { pathToFileURL } from "node:url";

const SKIP_DIRS = new Set(["_bundled", "node_modules", "__tests__"]);
const SKIP_FILE_RE = /\.(test|spec)\.[cm]?tsx?$/;

/** @type {typeof import("typescript")} */
let ts;

async function loadTypeScript(tsRoot) {
    const entry = path.join(tsRoot, "lib", "typescript.js");
    if (!fs.existsSync(entry)) {
        throw new Error(`typescript.js not found under ${tsRoot}`);
    }
    return import(pathToFileURL(entry).href);
}

function shouldSkipPath(fullPath, srcRoot) {
    const rel = path.relative(srcRoot, fullPath);
    if (!rel || rel.startsWith("..")) return true;
    return rel.split(path.sep).some((part) => SKIP_DIRS.has(part));
}

function walkTsFiles(srcRoot, acc = []) {
    for (const name of fs.readdirSync(srcRoot)) {
        const full = path.join(srcRoot, name);
        const rel = path.relative(srcRoot, full);
        if (rel.split(path.sep).some((part) => SKIP_DIRS.has(part))) continue;
        const stat = fs.statSync(full);
        if (stat.isDirectory()) {
            walkTsFiles(full, acc);
            continue;
        }
        if (!/\.[cm]?tsx?$/.test(name)) continue;
        if (SKIP_FILE_RE.test(name)) continue;
        acc.push(full);
    }
    return acc.sort();
}

function hasExportModifier(node) {
    return (
        ts.canHaveModifiers(node) &&
        (ts.getModifiers(node) ?? []).some((m) => m.kind === ts.SyntaxKind.ExportKeyword)
    );
}

function typeText(node, sourceFile, checker) {
    if (!node) return null;
    const type = checker.getTypeAtLocation(node);
    if (!type || type.flags & ts.TypeFlags.Any) {
        return checker.typeToString(type, node, ts.TypeFormatFlags.NoTruncation);
    }
    return checker.typeToString(type, node, ts.TypeFormatFlags.NoTruncation);
}

function serializeParameters(signature, sourceFile, checker) {
    const params = [];
    for (const param of signature.parameters ?? []) {
        const name = param.name.getText(sourceFile);
        if (name.startsWith("_")) continue;
        const optional = Boolean(param.questionToken || param.initializer);
        params.push({
            name,
            type: typeText(param, sourceFile, checker),
            optional,
        });
    }
    return params;
}

function serializeFunctionLike(node, sourceFile, checker, kind) {
    const signature = checker.getSignatureFromDeclaration(node);
    const sig = signature?.getDeclaration() ?? node;
    let returns = null;
    if (signature) {
        returns = checker.typeToString(
            checker.getReturnTypeOfSignature(signature),
            sig,
            ts.TypeFormatFlags.NoTruncation,
        );
    } else {
        returns = typeText(sig, sourceFile, checker);
    }
    return {
        kind,
        name: node.name?.getText(sourceFile) ?? "<anonymous>",
        async: Boolean(node.modifiers?.some((m) => m.kind === ts.SyntaxKind.AsyncKeyword)),
        params: serializeParameters(sig, sourceFile, checker),
        returns,
    };
}

function serializeProperty(member, sourceFile, checker) {
    const name = member.name.getText(sourceFile);
    if (name.startsWith("_") || name.startsWith("#")) return null;
    return {
        kind: member.kind === ts.SyntaxKind.MethodDeclaration ? "method" : "attribute",
        name,
        type: typeText(member, sourceFile, checker),
        optional: Boolean(member.questionToken),
    };
}

function serializeClassLike(node, sourceFile, checker, kind) {
    const members = [];
    const seen = new Set();
    for (const member of node.members ?? []) {
        if (
            ts.isMethodDeclaration(member) ||
            ts.isMethodSignature(member) ||
            ts.isPropertyDeclaration(member) ||
            ts.isPropertySignature(member) ||
            ts.isGetAccessorDeclaration(member) ||
            ts.isSetAccessorDeclaration(member)
        ) {
            if (ts.isMethodDeclaration(member) || ts.isMethodSignature(member)) {
                const memberName = member.name.getText(sourceFile);
                if (memberName.startsWith("_") || seen.has(memberName)) continue;
                seen.add(memberName);
                const payload = serializeFunctionLike(
                    member,
                    sourceFile,
                    checker,
                    "method",
                );
                payload.name = memberName;
                members.push(payload);
            } else {
                const payload = serializeProperty(member, sourceFile, checker);
                if (!payload || seen.has(payload.name)) continue;
                seen.add(payload.name);
                members.push(payload);
            }
        }
    }
    return {
        kind,
        name: node.name?.getText(sourceFile) ?? "<anonymous>",
        members,
        fields: members.filter((m) => m.kind === "attribute"),
    };
}

function serializeEnum(node, sourceFile) {
    const members = [];
    for (const member of node.members ?? []) {
        if (!ts.isEnumMember(member)) continue;
        const name = member.name.getText(sourceFile);
        let value = name;
        if (member.initializer) {
            value = member.initializer.getText(sourceFile).replace(/^["'`]|["'`]$/g, "");
        }
        members.push({ name, value });
    }
    return {
        kind: "enum",
        name: node.name.text,
        members,
    };
}

function isExported(node) {
    return hasExportModifier(node) || ts.isExportAssignment(node);
}

function extractFile(filePath, program, checker, srcRoot) {
    const sourceFile = program.getSourceFile(filePath);
    if (!sourceFile) return null;
    const declarations = [];
    const moduleDoc =
        ts.getLeadingCommentRanges(sourceFile.text, sourceFile.getFullStart())?.[0] != null
            ? sourceFile.text.slice(0, 200).match(/\/\*\*([\s\S]*?)\*\//)?.[1]?.trim() ?? ""
            : "";

    function visit(node) {
        const exported = isExported(node);
        if (ts.isInterfaceDeclaration(node) && exported) {
            declarations.push(serializeClassLike(node, sourceFile, checker, "interface"));
        } else if (ts.isClassDeclaration(node) && exported) {
            declarations.push(serializeClassLike(node, sourceFile, checker, "class"));
        } else if (ts.isEnumDeclaration(node) && exported) {
            declarations.push(serializeEnum(node, sourceFile));
        } else if (ts.isFunctionDeclaration(node) && exported && node.name) {
            const fname = node.name.text;
            if (fname.startsWith("_")) {
                ts.forEachChild(node, visit);
                return;
            }
            declarations.push(serializeFunctionLike(node, sourceFile, checker, "function"));
        } else if (ts.isTypeAliasDeclaration(node) && exported) {
            declarations.push({
                kind: "type_alias",
                name: node.name.text,
                type: typeText(node.type, sourceFile, checker),
            });
        } else if (ts.isVariableStatement(node) && exported) {
            for (const decl of node.declarationList.declarations) {
                if (!ts.isIdentifier(decl.name)) continue;
                const name = decl.name.text;
                if (name.startsWith("_")) continue;
                const kind = name === name.toUpperCase() ? "constant" : "variable";
                declarations.push({
                    kind,
                    name,
                    type: typeText(decl, sourceFile, checker),
                    value: decl.initializer?.getText(sourceFile) ?? null,
                });
            }
        }
        ts.forEachChild(node, visit);
    }

    visit(sourceFile);
    const rel = path.relative(srcRoot, filePath);
    return {
        path: rel.split(path.sep).join("/"),
        module: rel.replace(/\.[cm]?tsx?$/, "").split(path.sep).join("/"),
        doc: moduleDoc.split("\n")[0]?.replace(/^\s*\*\s?/, "") ?? "",
        declarations,
    };
}

function buildTree(modules, rootName) {
    const tree = { name: rootName, kind: "directory", children: {} };
    for (const module of modules) {
        const parts = String(module.path || "").split("/");
        let cursor = tree.children;
        for (const part of parts.slice(0, -1)) {
            const node = cursor[part] ?? {
                name: part,
                kind: "directory",
                children: {},
            };
            cursor[part] = node;
            cursor = node.children;
        }
        const leaf = parts[parts.length - 1];
        cursor[leaf] = {
            name: leaf,
            kind: "file",
            path: module.path,
            module: module.module,
            declaration_count: module.declarations.length,
        };
    }
    return tree;
}

function main() {
    return mainAsync().catch((err) => {
        console.error(err);
        process.exit(1);
    });
}

async function mainAsync() {
    const srcRoot = path.resolve(process.argv[2] ?? "");
    const tsRoot = path.resolve(process.argv[3] ?? path.join(path.dirname(srcRoot), "node_modules", "typescript"));
    if (!srcRoot || !fs.existsSync(srcRoot)) {
        console.error("Usage: structure-typescript.mjs <srcRoot> [typescriptPkgRoot]");
        process.exit(1);
    }

    const tsModule = await loadTypeScript(tsRoot);
    ts = tsModule.default ?? tsModule;

    const files = walkTsFiles(srcRoot);
    const configPath = ts.findConfigFile(path.dirname(srcRoot), ts.sys.fileExists, "tsconfig.json");
    const configFile = configPath
        ? ts.readConfigFile(configPath, ts.sys.readFile)
        : { config: {} };
    const parsed = ts.parseJsonConfigFileContent(
        configFile.config,
        ts.sys,
        path.dirname(configPath ?? srcRoot),
    );
    parsed.fileNames = files;
    const program = ts.createProgram({
        rootNames: files,
        options: parsed.options,
    });
    const checker = program.getTypeChecker();

    const modules = [];
    for (const filePath of files) {
        const payload = extractFile(filePath, program, checker, srcRoot);
        if (payload) modules.push(payload);
    }

    const sdkRoot = path.dirname(srcRoot);
    const result = {
        language: "typescript",
        sdk_root: sdkRoot,
        package: path.basename(srcRoot),
        module_count: modules.length,
        modules,
        tree: buildTree(modules, path.basename(srcRoot)),
    };

    const json = JSON.stringify(result, null, 2);
    process.stdout.write(json);
}

main();
