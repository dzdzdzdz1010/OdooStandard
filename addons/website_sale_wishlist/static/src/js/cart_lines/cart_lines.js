import { rpc } from '@web/core/network/rpc';
import { patch } from '@web/core/utils/patch';
import { CartLines } from '@website_sale/js/cart_lines/cart_lines';
import wishlistUtils from '@website_sale_wishlist/js/website_sale_wishlist_utils';


patch(CartLines.prototype, {
    async addToWishlist(lineId, productId) {
        await rpc('/shop/wishlist/add', { product_id: productId });
        wishlistUtils.addWishlistProduct(productId);
        wishlistUtils.updateWishlistNavBar();
        this.updateLine(lineId, productId, 0);
    },
});
