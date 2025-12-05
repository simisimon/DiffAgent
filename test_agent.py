"""Test script for the DiffAgent."""

from agent import DiffAgent
from dotenv import load_dotenv

# Sample diff with a configuration inconsistency
TEST_DIFF = """diff --git a/src/Dockerfile b/src/Dockerfile
index 9b6c00d..0389651 100644
--- a/src/Dockerfile
+++ b/src/Dockerfile
@@ -18,7 +18,7 @@ WORKDIR /app
 COPY --from=build /app/target/spring-boot-app-0.0.1-SNAPSHOT.jar app.jar

 # Expose the application port
-EXPOSE 8080
+EXPOSE 8000

 # Run the application
 ENTRYPOINT ["java", "-jar", "app.jar"]


diff --git a/src/application.properties b/src/application.properties
index 9eedcd6..c636ea5 100644
--- a/src/application.properties
+++ b/src/application.properties
@@ -1,5 +1,5 @@
 server.name = localhost
-server.port = 8080
+server.port = 8000
"""


def test_basic_validation():
    """Test basic validation with a sample diff."""
    print("Testing DiffAgent with sample configuration changes...")
    print()

    # Load environment variables
    load_dotenv()

    # Create agent
    agent = DiffAgent()

    # Validate the diff
    result = agent.validate_diff(TEST_DIFF, commit_hash="test-001")

    # Print results
    agent.print_result(result)

    return result


def test_consistent_diff():
    """Test with a diff that has no errors."""
    consistent_diff = """diff --git a/config/settings.yml b/config/settings.yml
index abc123..def456 100644
--- a/config/settings.yml
+++ b/config/settings.yml
@@ -1,3 +1,3 @@
 app:
   name: MyApp
-  debug: false
+  debug: true
"""

    print("\n\nTesting with consistent configuration change...")
    print()

    agent = DiffAgent()
    result = agent.validate_diff(consistent_diff)
    agent.print_result(result)

    return result


def test_security_issue():
    """Test detection of security-related configuration issues."""
    security_diff = """diff --git a/.env b/.env
index abc123..def456 100644
--- a/.env
+++ b/.env
@@ -1,2 +1,2 @@
-DEBUG=false
+DEBUG=true
-ALLOWED_HOSTS=myapp.com
+ALLOWED_HOSTS=*
"""

    print("\n\nTesting security issue detection...")
    print()

    agent = DiffAgent()
    result = agent.validate_diff(security_diff)
    agent.print_result(result)

    return result


if __name__ == "__main__":
    # Run tests
    print("Starting DiffAgent Tests")
    print("=" * 80)
    print()

    try:
        # Test 1: Basic validation
        result1 = test_basic_validation()

        # Test 2: Consistent changes
        result2 = test_consistent_diff()

        # Test 3: Security issues
        result3 = test_security_issue()

        print("\n" + "=" * 80)
        print("All tests completed!")
        print("=" * 80)

    except Exception as e:
        print(f"\nError during testing: {e}")
        import traceback
        traceback.print_exc()
