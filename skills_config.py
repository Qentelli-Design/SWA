"""Centralized skill category configuration.

Keep category lists here. Import this module where needed; avoid duplicating the mapping.
"""

SKILL_CATEGORIES = {
    "UI / Web Automation": [
        "AccelQ",
        "Browser stack testing",
        "Codecept JS",
        "Cypress",
        "Playwright",
        "Playwright with Java",
        "Playwright with JavaScript",
        "Playwright with Python",
        "Playwright with TypeScript",
        "Selenium",
        "Selenium with C#",
        "Selenium with Java",
        "Web Automation",
        "WebDriverIO",
    ],

    "Mobile Automation": [
        "Appium",
        "Mobile Automation",
        "XCUITest",
    ],

    "Test Frameworks / BDD": [
        "BDD Framework",
        "JUnit",
        "Karate Framework",
        "Katalon Studio",
        "LeanFT",
        "Mocha",
        "NUnit",
        "Pytest",
        "Robot Framework",
        "Serenity",
        "TestNG",
        "Tosca",
        "UFT Vbscript Automation",
    ],

    "API / Service Testing": [
        "API Testing",
        "Postman",
        "SoapUI",
        "RestAssured",
    ],

    "Programming / Development": [
        "Java",
        "C#",
        "Python",
        "JavaScript",
        "TypeScript",
        "Node.js",
    ],

    "Database / Data": [
        "SQL",
        "NoSQL",
        "ETL",
        "Data Engineering",
    ],

    "DevOps / CI-CD / Source Control": [
        "Git",
        "Jenkins",
        "Azure DevOps",
        "CircleCI",
        "Docker",
        "Kubernetes",
    ],

    "Cloud / AWS": [
        "AWS",
        "Azure",
        "GCP",
    ],

    "AI / GenAI / AI Tools": [
        "ChatGPT",
        "GenAI",
        "ML",
    ],

    "Test Management / Collaboration": [
        "Jira",
        "Confluence",
        "TestRail",
    ],

    "Performance / Messaging / Observability": [
        "JMeter",
        "Gatling",
        "Kafka",
        "Prometheus",
    ],

    "Specialized / Other": [
        "Accessibility",
        "Security Testing",
        "Review",
    ],
}

# Label to use for unknown skills
UNCATEGORIZED_LABEL = "Uncategorized / Review"
