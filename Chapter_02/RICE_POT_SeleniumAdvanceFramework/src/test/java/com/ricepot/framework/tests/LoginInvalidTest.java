package com.ricepot.framework.tests;

import com.ricepot.framework.base.BaseTest;
import com.ricepot.framework.pages.LoginPage;
import org.testng.Assert;
import org.testng.annotations.BeforeTest;
import org.testng.annotations.Test;

public class LoginInvalidTest extends BaseTest {

    private LoginPage loginPage;

    @BeforeTest
    public void setupLoginPage() {
        loginPage = new LoginPage(driver, wait);
    }

    @Test
    public void invalidLoginShouldShowError() {
        String username = System.getProperty("salesforce.invalidUsername", "invalid.user@company.com");
        String password = System.getProperty("salesforce.invalidPassword", "WrongPassword123");

        try {
            loginPage.open("https://login.salesforce.com/?locale=in");
            loginPage.login(username, password);
            Assert.assertTrue(loginPage.isErrorDisplayed(), "Expected an invalid login error message.");
        } catch (Exception e) {
            Assert.fail("Invalid login test failed: " + e.getMessage());
        }
    }
}
