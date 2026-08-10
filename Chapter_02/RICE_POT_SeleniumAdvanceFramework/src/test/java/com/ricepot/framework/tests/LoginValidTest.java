package com.ricepot.framework.tests;

import com.ricepot.framework.base.BaseTest;
import com.ricepot.framework.pages.LoginPage;
import org.testng.Assert;
import org.testng.annotations.BeforeTest;
import org.testng.annotations.Test;

public class LoginValidTest extends BaseTest {

    private LoginPage loginPage;

    @BeforeTest
    public void setupLoginPage() {
        loginPage = new LoginPage(driver, wait);
    }

    @Test
    public void validLoginShouldComplete() {
        String username = System.getProperty("salesforce.username");
        String password = System.getProperty("salesforce.password");

        if (username == null || username.trim().isEmpty() || password == null || password.trim().isEmpty()) {
            Assert.fail("Missing Salesforce credentials. Supply -Dsalesforce.username and -Dsalesforce.password");
        }

        try {
            loginPage.open("https://login.salesforce.com/?locale=in");
            loginPage.login(username, password);
            Assert.assertTrue(loginPage.isLoginSuccessful(), "Expected a successful login flow.");
        } catch (Exception e) {
            Assert.fail("Valid login test failed: " + e.getMessage());
        }
    }
}
