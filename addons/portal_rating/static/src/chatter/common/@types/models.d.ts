declare module "models" {
    export interface Thread {
        rating_stats: { avg: number, total: number, percent: Object<number, number>};
    }
}
