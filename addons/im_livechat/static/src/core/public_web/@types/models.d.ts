declare module "models" {
    export interface DiscussChannel {
        appAsLivechats: DiscussApp;
        livechatStatusLabel: Readonly<string>;
        matchesSelfExpertise: Readonly<boolean>;
        shadowedBySelf: number;
        updateLivechatStatus: (status: "in_progress"|"waiting"|"need_help") => void;
    }
    export interface LivechatChannel {
        appCategory: DiscussAppCategory;
    }
}
