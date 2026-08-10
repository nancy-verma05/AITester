package com.ricepot.framework.pages;

import org.openqa.selenium.WebDriver;
import org.openqa.selenium.WebElement;
import org.openqa.selenium.support.FindBy;
import org.openqa.selenium.support.PageFactory;
import org.openqa.selenium.support.ui.ExpectedConditions;
import org.openqa.selenium.support.ui.WebDriverWait;

public class LoginPage {

    private final WebDriver driver;
    private final WebDriverWait wait;

    @FindBy(xpath = "//*[@id='username']")
    private WebElement username;

    @FindBy(xpath = "//*[@id='password']")
    private WebElement password;

    @FindBy(xpath = "//*[@id='Login']")
    private WebElement loginButton;

    @FindBy(xpath = "//*[contains(@class,'error') or contains(@id,'error')]")
    private WebElement errorMessage;

    public LoginPage(WebDriver driver, WebDriverWait wait) {
        this.driver = driver;
        this.wait = wait;
        PageFactory.initElements(driver, this);
    }

    public void open(String url) {
        try {
            driver.get(url);
        } catch (Exception e) {
            throw new RuntimeException("Unable to open Salesforce login page: " + url, e);
        }
    }

    public void enterUsername(String userName) {
        try {
            wait.until(ExpectedConditions.visibilityOf(username)).clear();
            username.sendKeys(userName);
        } catch (Exception e) {
            throw new RuntimeException("Failed to enter username in Salesforce login page", e);
        }
    }

    public void enterPassword(String passWord) {
        try {
            wait.until(ExpectedConditions.visibilityOf(password)).clear();
            password.sendKeys(passWord);
        } catch (Exception e) {
            throw new RuntimeException("Failed to enter password in Salesforce login page", e);
        }
    }

    public void clickLoginButton() {
        try {
            wait.until(ExpectedConditions.elementToBeClickable(loginButton)).click();
        } catch (Exception e) {
            throw new RuntimeException("Failed to click Salesforce login button", e);
        }
    }

    public void login(String userName, String passWord) {
        try {
            enterUsername(userName);
            enterPassword(passWord);
            clickLoginButton();
        } catch (Exception e) {
            throw new RuntimeException("Login flow failed", e);
        }
    }

    public boolean isErrorDisplayed() {
        try {
            wait.until(ExpectedConditions.visibilityOf(errorMessage));
            return true;
        } catch (Exception e) {
            return false;
        }
    }

    public String getErrorMessage() {
        try {
            return wait.until(ExpectedConditions.visibilityOf(errorMessage)).getText();
        } catch (Exception e) {
            return "";
        }
    }

    public boolean isLoginSuccessful() {
        try {
            return driver.getCurrentUrl() != null && !driver.getCurrentUrl().contains("login");
        } catch (Exception e) {
            return false;
        }
    }
}
