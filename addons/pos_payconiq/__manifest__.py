{
    "name": "POS Payconiq",
    "category": "Sales/Point of Sale",
    "sequence": 100,
    "summary": "Accept Payconiq payments via Instant QR codes in your POS",
    "data": ["views/pos_payment_method_views.xml"],
    "depends": ["point_of_sale"],
    "assets": {
        "point_of_sale._assets_pos": [
            "pos_payconiq/static/src/**/*",
        ],
        "web.assets_tests": [
            "pos_payconiq/static/tests/tours/**/*",
        ],
        "web.assets_unit_tests": [
            "pos_payconiq/static/tests/unit/**/*",
        ],
    },
    "author": "Odoo S.A.",
    "license": "LGPL-3",
}
