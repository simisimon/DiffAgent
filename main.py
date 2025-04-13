
from agent import CommitDiffValidator
from dotenv import load_dotenv
from openai import OpenAI
from os import getenv

test_diff = """diff --git a/src/Dockerfile b/src/Dockerfile
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
 
 spring.datasource.url = jdbc:mysql://localhost:3306/employee
 spring.datasource.username = root"""

range_constraint = """diff --git a/src/Dockerfile b/src/Dockerfile
index 0389651..4a62912 100644
--- a/src/Dockerfile
+++ b/src/Dockerfile
@@ -18,7 +18,7 @@ WORKDIR /app
 COPY --from=build /app/target/spring-boot-app-0.0.1-SNAPSHOT.jar app.jar
 
 # Expose the application port
-EXPOSE 8000
+EXPOSE 10000123330
 
 # Run the application
 ENTRYPOINT ["java", "-jar", "app.jar"]"""


def generate_test() :
    
    client = OpenAI(
        api_key=getenv("OPENAI_API_KEY"),
        #api_key=getenv("PROXY_SERVER_API_KEY"),
        #base_url=getenv("BASE_URL")
    )

    messages = [
        {"role": "system", "content": "Hi"},
        {"role": "user", "content": "What's up?"}
    ]

    response = client.chat.completions.create(
        model="gpt-4o-mini", 
        messages=messages,        
        temperature=0.0,
        max_tokens=100,
        timeout=90
    )

    print(response.choices[0].message.content)


def main():

    load_dotenv(dotenv_path=".env")

    #generate_test()

    agent = CommitDiffValidator()
    agent.run(commit_diff=test_diff)

if __name__ == "__main__":
    main()