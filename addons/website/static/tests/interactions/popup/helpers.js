/**
 * Generate age verification popup template.
 *
 * @param {Object} [options]
 * @param {string} [options.confirmationType="yes_or_no"]
 * @param {number} [options.minAge=18]
 * @param {string} [options.errorMessage="You must be older to continue!"]
 * @returns {string} Age verification popup template
 */
export function getAgeVerificationTemplate(options = {}) {
    const {
        confirmationType = "yes_or_no",
        minAge = 18,
        errorMessage = "You must be older to continue!",
    } = options;

    const TEMPLATES = {
        yes_or_no: `
            <div>
                <a href="#" class="o_age_verification_yes_btn oe_unremovable">Yes</a>
                <a href="#" class="o_age_verification_no_btn oe_unremovable">No</a>
            </div>
        `,
        birth_year: `
            <div>
                <input
                    type="number"
                    class="form-control o_age_verification_birth_year"
                    name="birth_year"
                    min="1900"
                    placeholder="Enter your birth year"
                />
                <a href="#" class="o_age_verify_year_btn oe_unremovable">Verify</a>
            </div>
        `,
        birth_date: `
            <div>
                <div class="input-group">
                    <input
                        type="text"
                        class="form-control o_age_verification_birth_date"
                        name="birth_date"
                        placeholder="Enter your birth date"
                    />
                    <div><i class="fa fa-calendar"></i></div>
                </div>
                <p><a href="#" class="o_age_verify_date_btn oe_unremovable">Verify</a></p>
            </div>
        `,
    };

    return `
        <div class="s_popup s_age_verification_popup o_snippet_invisible" data-vcss="001" id="sAgeVerificationPopup" data-invisible="1">
            <div class="modal fade s_popup_middle" tabindex="-1" role="dialog"
                data-bs-focus="false" data-bs-backdrop="false" data-bs-keyboard="false"
                data-min-age="${minAge}" data-show-after="0" data-display="afterDelay" data-consents-duration="30">
                <div class="modal-dialog">
                    <div class="modal-content oe_structure">
                        <div id="verification_error" class="d-none">
                            <span>${errorMessage}</span>
                        </div>
                        <section>
                            <div>
                                <h2>Are you 18 years or older?</h2>
                                <p>Our services are available only to adults of legal age.</p>
                            </div>
                            <div id="age_confirmation_block" class="oe_unremovable">
                                <div class="row">
                                    ${TEMPLATES[confirmationType]}
                                </div>
                            </div>
                        </section>
                    </div>
                </div>
            </div>
        </div>
    `;
}
