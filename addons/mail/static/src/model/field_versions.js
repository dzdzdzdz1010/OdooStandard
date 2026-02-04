/**
 * @typedef {{xmin: number, xmax: number, xip: number[], current_xact_id: number|null}} IPgSnapshot
 * @typedef {{snapshot: PgSnapshot|null, isWrite: boolean}} FieldRevision
 */

export class PgSnapshot {
    /** @param {IPgSnapshot} */
    constructor(params) {
        this.current_xact_id = params.current_xact_id;
        this.xmin = params.xmin;
        this.xmax = params.xmax;
        this.xip = new Set(params.xip);
    }

    get transactionCount() {
        return this.xmax - 1 - this.xip.size;
    }

    /**
     * Determine whether the given transaction was visibile by this snapshot.
     *
     * @param {number} txid
     */
    knowsTransaction(txid) {
        // tx < xmin are visible. tx between xmin and xmax are visible if not in xip.
        // See: https://www.postgresql.org/docs/13/functions-info.html#FUNCTIONS-PG-SNAPSHOT-PARTS
        return txid < this.xmin || (txid < this.xmax && !this.xip.has(txid));
    }

    /**
     * Determine whether the given revision comes from a newer snapshot than the current
     * one (i.e. if the given revision knows more committed transactions than the current
     * one).
     *
     * @param {PgSnapshot} other
     */
    isAfter(other) {
        return this.transactionCount > other.transactionCount;
    }

    /**
     * Determine if a snapshot has the same horizon than this snapshot. (i.e. they saw the
     * same DB version).
     *
     * @param {PgSnapshot} other
     */
    hasSameHorizon(other) {
        return this.transactionCount === other.transactionCount;
    }
}

/**
 * Determine if a candidate revision can override the other revision.
 *
 * @param {FieldRevision} candidate
 * @param {FieldRevision} other
 * @returns {Boolean} Whether the incoming revision can override the current one.
 */
function canOverride(candidate, other) {
    if (candidate.snapshot.hasSameHorizon(other.snapshot)) {
        return true;
    }
    // candidate is a read:
    // - vs write: can override if the candidate revision knows about the transaction the
    //   write originates from.
    // - vs read: can override if the candidate revision comes from a newer snapshot (i.e.
    //   this revision knows more committed transactions).
    if (!candidate.isWrite) {
        return other.isWrite
            ? candidate.snapshot.knowsTransaction(other.snapshot.current_xact_id)
            : candidate.snapshot.isAfter(other.snapshot);
    }
    // Candidate is a write: we can override any revision that didn't know
    // about this transaction.
    return !other.snapshot.knowsTransaction(candidate.snapshot.current_xact_id);
}

export const SKIP_REVISION = Symbol("SKIP");

/**
 * Track a single value field's latest revision and allow to determine if a new value can
 * be applied based on snapshot visibility.
 */
export class SingleFieldVersion {
    lastRevision = { snapshot: new PgSnapshot({ xmin: 0, xmax: 0, xip: [] }), isWrite: false };

    /** Determine if the current revision can override the given one.
     *
     * @template T
     * @param {T} value
     * @param {FieldRevision} incomingRevision
     * @returns {typeof SKIP_REVISION|T} The skip symbol, or the value to update the
     * field.
     */
    resolveApply(value, incomingRevision) {
        if (canOverride(incomingRevision, this.lastRevision)) {
            this.lastRevision = incomingRevision;
            return value;
        }
        return SKIP_REVISION;
    }
}

/**
 * Track a multi value field's command history and determine which commands can be applied
 * based on revision snapshots.
 */
export class ManyFieldVersion {
    /** @type {import("@mail/model/record").Record} */
    TargetModel;
    /**
     * Tracks the command history for this field, in chronological order. Each entry
     * represents a single command along with the revision at which it was applied.
     *
     * @type {{cmd: [], revision: FieldRevision}[]}
     */
    history = [
        {
            cmd: ["REPLACE", []],
            revision: { snapshot: new PgSnapshot({ xmin: 0, xmax: 0, xip: [] }), isWrite: false },
        },
    ];

    constructor(TargetModel) {
        this.TargetModel = TargetModel;
    }

    /**
     * Determine what commands should be applied.
     *
     * @param {Array[]} commands
     * @param {FieldRevision} incomingRevision
     * @returns {Array[]|typeof SKIP_REVISION} The skip symbol, or the commands to apply
     * to update the field.
     */
    resolveApply(commands, incomingRevision) {
        if (!canOverride(incomingRevision, this.history[0].revision)) {
            return SKIP_REVISION;
        }
        const insertionIndex = this._findInsertionIndex(incomingRevision);
        const insertAtTheEnd = insertionIndex === this.history.length;
        this.history.splice(
            insertionIndex,
            0,
            ...commands.map((cmd) => ({ cmd, revision: incomingRevision }))
        );
        if (insertAtTheEnd) {
            return commands;
        }
        const lastReplaceIndex = this.history.findLastIndex((entry) => entry.cmd[0] === "REPLACE");
        if (lastReplaceIndex >= insertionIndex) {
            this.history = this.history.slice(lastReplaceIndex);
        }
        return this._generateReplaceFromHistory();
    }

    /**
     * Returns the index of the first element strictly greater than the given revision.
     * This ensures identical revisions are kept in their original arrival order.
     *
     * @param {FieldRevision} revision
     */
    _findInsertionIndex(revision) {
        let start = 0;
        let end = this.history.length;
        while (start < end) {
            const mid = Math.floor((start + end) / 2);
            const midRevision = this.history[mid].revision;
            if (canOverride(revision, midRevision)) {
                start = mid + 1;
            } else {
                end = mid;
            }
        }
        return start;
    }

    get lastRevision() {
        return this.history.at(-1).revision;
    }

    /** Returns a replace command, equivalent to all the commands in history. */
    _generateReplaceFromHistory() {
        const positionByLocalId = {};
        for (let idx = 0; idx < this.history.length; idx++) {
            const [name, values] = this.history[idx].cmd;
            for (let subIdx = 0; subIdx < values.length; subIdx++) {
                const value = values[subIdx];
                const localId = this.TargetModel.localId(value);
                if (["REPLACE", "ADD", "ADD.noinv"].includes(name)) {
                    positionByLocalId[localId] ??= { value, idx, subIdx };
                } else {
                    delete positionByLocalId[localId];
                }
            }
        }
        const sortedValues = Object.values(positionByLocalId)
            .sort((a, b) => a.idx - b.idx || a.subIdx - b.subIdx)
            .map((p) => p.value);
        return [["REPLACE", sortedValues]];
    }
}
