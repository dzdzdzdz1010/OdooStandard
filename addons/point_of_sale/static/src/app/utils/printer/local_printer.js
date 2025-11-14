import { _t } from "@web/core/l10n/translation";
import { BasePrinter } from "@point_of_sale/app/utils/printer/base_printer";

const ERROR_CODES = {
    PRINTER_NOT_FOUND: "PRINTER_NOT_FOUND",
    CONNECTION_FAILED: "CONNECTION_FAILED",
    PRINT_FAILED: "PRINT_FAILED",
};

export class LocalPrinter extends BasePrinter {
    async setup({ printer }) {
        super.setup(...arguments);
        this.printer = printer.local_printer_data || {};
    }

    async openCashbox() {
        await this._execute("cash_drawer");
    }

    async sendPrintingJob(image) {
        return this._execute("print_receipt", { image });
    }

    async _execute(action, data = null) {
        try {
            const response = await window.action({
                action,
                device: JSON.parse(JSON.stringify(this.printer)),
                data,
            });

            if (response?.status === true) {
                return {
                    result: true,
                    message: response.message || "Print job sent successfully",
                    canRetry: false,
                };
            } else {
                return this._getErrorResult(
                    response.error_code && ERROR_CODES[response.error_code]
                        ? response.error_code
                        : ERROR_CODES.PRINT_FAILED
                );
            }
        } catch {
            return this._getErrorResult(ERROR_CODES.CONNECTION_FAILED);
        }
    }

    _getErrorResult(errorCode) {
        const errorMessages = {
            [ERROR_CODES.PRINTER_NOT_FOUND]: {
                title: _t("Printer Not Found"),
                body: _t("No printer is available. Please check printer connection and try again."),
            },
            [ERROR_CODES.CONNECTION_FAILED]: {
                title: _t("Connection Failed"),
                body: _t("Failed to connect to printer service."),
            },
            [ERROR_CODES.PRINT_FAILED]: {
                title: _t("Printing Failed"),
                body: _t("Failed to print. Please check printer status and try again."),
            },
        };

        const message = errorMessages[errorCode] || errorMessages[ERROR_CODES.CONNECTION_FAILED];

        return {
            result: false,
            errorCode,
            canRetry: true,
            message: {
                title: message.title,
                body: message.body,
            },
        };
    }

    getActionError() {
        const actionError = super.getResultsError();
        actionError.message.body += _t(
            "Please check that the printer is turned on and connected, then try again."
        );
        return actionError;
    }

    getResultsError(printResult) {
        return printResult || this._getErrorResult(ERROR_CODES.CONNECTION_FAILED);
    }
}
