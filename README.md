# Nimbus
![](cloudy_robot_400.png)

### AWS Lambda
1. Lambda management is done with [Apex](http://apex.run/)
2. Install Apex ```sudo curl https://raw.githubusercontent.com/apex/apex/master/install.sh | sh```
3. Run ```apex init```
4. Run ```pip install -r requirements.txt -t functions/nimbus``` 
5. Set "timeout": 60 in the ```project.json``` file.
6. Go to [Identity and Access Management](https://console.aws.amazon.com/iam/home?region=us-east-1#roles)
6. Select nimbus_lambda_function
7. Attache the following policies
 *   A. AmazonEC2ReadOnlyAccess
 *   B. AmazonRoute53ReadOnlyAccess
 *   C. AmazonDynamoDBReadOnlyAccess

### AWS API Gateway
1. Go to [AWS API Gateway](https://console.aws.amazon.com/apigateway/home?region=us-east-1#/apis).
2. Click "Get Started Now".
3. Under "API name", enter the name of your API. I will just name it "nimbus".
4. Click "Create API".
5. You will be redirected to the "Resources" page.
6. Click "Create Method" and on the dropdown menu on the left, choose "POST" and click on the "tick" icon.
7. Now, you will see the "/ - POST - Setup" page on the right.
8. Under "Integration Type", choose "Lambda Function".
9. Under "Lambda Region", choose "us-east-1".
10. Under "Lambda Function", type "nimbus" and it should auto-complete it to "nimbus_nimbus".
11. Click "Save" and "Ok" when the popup appears.
12. You will be brought to the "/ - POST - Method Execution" Page.
13. Click "Integration Request".
14. Click "Mapping Templates" and the section should expand.
15. Click "Add Mapping Template" and type in "application/x-www-form-urlencoded" and click on the "tick" icon.
16. Under "Input Passthrough" on the right, click on the "pencil" icon.
16. Choose "Mapping Template" on the dropdown that appears.
17. Copy and paste [this GitHub Gist](https://gist.githubusercontent.com/avivl/2b68205413fc88c11aa002835f974d50/raw/76ae883a770b541365910cbb48249d7b155c7455/aws-api-gateway-form-to-json) to the template box.
18. Click on the "tick" icon beside the dropdown once you are done.
19. This GitHub Gist will covert the your API Gateway data from application/x-www-form-urlencoded to application/json.
20. Click on "Deploy API" button on the top left.
21. Under "Deployment Stage", click "New Stage".
22. Under "Stage Name", I will type in "prod".
23. Click "Deploy".
24. Note the "Invoke URL" at the top and your API is now live.

### Slack
1. Go to [Slack Apps](https://slack.com/apps).
2. Search for "Outgoing WebHooks".
3. Click "Install" besides the team you wanted.
4. Click "Add Outgoing WebHook Integration".
5. Scroll down to "Integration Settings" section.
6. Under "Channel", choose "Any".
7. Under "Trigger Word(s)", type in "nimbus" (without the quotes).
8. Under "URL(s)", type in your "Invoke URL" as noted above.
9. Customize "Descriptive Label", "Name" and "Icon" (you can use cloudy_robot_200.png from the nimbus repo) )to your liking and click "Save Settings".
10. Copy the Token value.
11. You are all set.

### Configuration data
1. Go to [Identity and Access Management](https://console.aws.amazon.com/iam/home?region=us-east-1#encryptionKeys/us-east-1)
2. Create the following mandatory keys - SlackAPIKey (Slack AP Token),  nimbus (Slack verification token)
3. Create optional keys - DigitalOcean (DigitalOcean API key)
4. For each of the created keys do the following
    ```$ aws kms encrypt --key-id alias/<KMS key name> --plaintext "<COMMAND_TOKEN>"```
5. Copy the base-64 encoded, encrypted key
6. Go to [DynamoDB](https://console.aws.amazon.com/dynamodb/home?region=us-east-1) and create a table by the name of nimbus
7. Add the following items to the table:
 *   A. BotName - Default "Nimbus"
 *   B. DigitalOcean - Encrypted DigitalOcean key
 *   C. SlackAPI - Encrypted SlackAPI Token
 *   D. SlackExpected - Encrypted Slack verification token
 *   E. icon - Url for the bot icon
8. Give your function's role permission for the kms:Decrypt action.
   Example:
     {
       "Version": "2012-10-17",
       "Statement": [
         {
           "Effect": "Allow",
           "Action": [
             "kms:Decrypt"
           ],
           "Resource": [
             "<your KMS key ARN>"
           ]
         }
       ]
     }


### Ready set Go!

You can deploy your code by running ```apex deploy```
