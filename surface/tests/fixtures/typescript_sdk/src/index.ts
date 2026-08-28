export class PortoMark {
    id!: string;
}

export class ProviderClient {
    /** Bound execution context for one postal provider. */
    resolve(countryFrom: string): string {
        return countryFrom;
    }

    /** Purchase a mark. */
    mark(): Promise<PortoMark> {
        return Promise.resolve(new PortoMark());
    }
}

export enum LetterType {
    SMALL = "small",
    MEDIUM = "medium",
}
