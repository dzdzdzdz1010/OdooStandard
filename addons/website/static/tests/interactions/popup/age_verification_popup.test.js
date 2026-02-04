import { describe, expect, test } from "@odoo/hoot";
import { animationFrame, tick } from "@odoo/hoot-dom";
import { mockDate } from "@odoo/hoot-mock";
import { setupInteractionWhiteList, startInteractions } from "@web/../tests/public/helpers";
import { contains } from "@web/../tests/web_test_helpers";
import { getAgeVerificationTemplate } from "./helpers";

setupInteractionWhiteList("website.age_verification_popup");
describe.current.tags("interaction_dev");

const modal = "#sAgeVerificationPopup .modal";
const getVerifyBtnSelector = (verificationType) => `${modal} .o_age_verify_${verificationType}_btn`;
const modalErrorMessage = `${modal} #verification_error span`;

async function setupAgeVerificationPopup(options = {}) {
    const { core } = await startInteractions(getAgeVerificationTemplate(options));
    await tick();
    await animationFrame();
    expect(core.interactions).toHaveLength(1);
    expect(modal).toBeVisible();
    expect(modalErrorMessage).not.toBeVisible();
    return core;
}

test("Yes button closes popup and No button displays the error message", async () => {
    await setupAgeVerificationPopup();
    await contains(`${modal} .o_age_verification_no_btn`).click();
    expect(modalErrorMessage).toBeVisible();
    expect(modalErrorMessage).toHaveText("You must be older to continue!");

    await contains(`${modal} .o_age_verification_yes_btn`).click();
    expect(modal).not.toBeVisible();
});

test("Using birth year input, Verify button closes popup when age meets minimum", async () => {
    mockDate("2025-11-14 12:00:00");
    await setupAgeVerificationPopup({
        confirmationType: "birth_year",
        minAge: 20,
        errorMessage: "Invalid age test",
    });
    const verifyBtn = getVerifyBtnSelector("year");
    expect(`${modal} .o_age_verification_birth_year.is-invalid`).toHaveCount(0);
    await contains(verifyBtn).click();
    expect(`${modal} .o_age_verification_birth_year.is-invalid`).toHaveCount(1);

    await contains(`${modal} .o_age_verification_birth_year`).edit("2006");
    await contains(verifyBtn).click();
    expect(modalErrorMessage).toBeVisible();
    expect(modalErrorMessage).toHaveText("Invalid age test");
    expect(`${modal} .o_age_verification_birth_year.is-invalid`).toHaveCount(0);

    await contains(`${modal} .o_age_verification_birth_year`).edit("1899");
    await contains(verifyBtn).click();
    expect(`${modal} .o_age_verification_birth_year.is-invalid`).toHaveCount(1);

    await contains(`${modal} .o_age_verification_birth_year`).edit("2026");
    await contains(verifyBtn).click();
    expect(`${modal} .o_age_verification_birth_year.is-invalid`).toHaveCount(1);

    await contains(`${modal} .o_age_verification_birth_year`).edit("1950.25");
    await contains(verifyBtn).click();
    expect(`${modal} .o_age_verification_birth_year.is-invalid`).toHaveCount(1);

    await contains(`${modal} .o_age_verification_birth_year`).edit("2000");
    await contains(verifyBtn).click();
    expect(modal).not.toBeVisible();
});

test("Using birth date input, Verify button closes popup when age meets minimum", async () => {
    mockDate("2025-11-14 12:00:00");
    await setupAgeVerificationPopup({
        confirmationType: "birth_date",
        minAge: 20,
        errorMessage: "Invalid age test",
    });
    const verifyBtn = getVerifyBtnSelector("date");
    expect(`${modal} .o_age_verification_birth_date.is-invalid`).toHaveCount(0);
    await contains(verifyBtn).click();
    expect(`${modal} .o_age_verification_birth_date.is-invalid`).toHaveCount(1);

    await contains(`${modal} .o_age_verification_birth_date`).edit("01/01/2006");
    await contains(verifyBtn).click();
    expect(modalErrorMessage).toBeVisible();
    expect(modalErrorMessage).toHaveText("Invalid age test");

    await contains(`${modal} .o_age_verification_birth_date`).edit("01/01/2004");
    await contains(verifyBtn).click();
    expect(modal).not.toBeVisible();
});
