# Nimbus
![Nimbus Logo](cloudy_robot.png)

### AWS Lambda
1. Lambda management is done with [Apex](http://apex.run/)
1. Install Apex `sudo curl https://raw.githubusercontent.com/apex/apex/master/install.sh | sh`
1. Run `apex init`
1. Run `pip install -r requirements.txt -t functions/nimbus`
1. Set `timeout` to 60 in the `project.json` file.
1. Go to [Identity and Access Management](https://console.aws.amazon.com/iam/home?region=us-east-1#roles)
1. Select nimbus_lambda_function
1. Attach the following policies
  1. AmazonEC2ReadOnlyAccess
  1. AmazonRoute53ReadOnlyAccess
  1. AmazonDynamoDBReadOnlyAccess

### AWS API Gateway
1. Go to [AWS API Gateway](https://console.aws.amazon.com/apigateway/home?region=us-east-1#/apis).
1. Click "Get Started Now".
1. Under "API name", enter the name of your API. I will just name it "nimbus".
1. Click "Create API".
1. You will be redirected to the "Resources" page.
1. Click "Create Method" and on the dropdown menu on the left, choose "POST" and click on the "tick" icon.
1. Now, you will see the "/ - POST - Setup" page on the right.
1. Under "Integration Type", choose "Lambda Function".
1. Under "Lambda Region", choose "us-east-1".
1. Under "Lambda Function", type "nimbus" and it should auto-complete it to "nimbus_nimbus".
1. Click "Save" and "Ok" when the popup appears.
1. You will be brought to the "/ - POST - Method Execution" Page.
1. Click "Integration Request".
1. Click "Mapping Templates" and the section should expand.
1. Click "Add Mapping Template" and type in "application/x-www-form-urlencoded" and click on the "tick" icon.
1. Under "Input Passthrough" on the right, click on the "pencil" icon.
1. Choose "Mapping Template" on the dropdown that appears.
1. Copy and paste [this GitHub Gist](https://gist.githubusercontent.com/avivl/2b68205413fc88c11aa002835f974d50/raw/76ae883a770b541365910cbb48249d7b155c7455/aws-api-gateway-form-to-json) to the template box.
1. Click on the "tick" icon beside the dropdown once you are done.
1. This GitHub Gist will covert the your API Gateway data from application/x-www-form-urlencoded to application/json.
1. Click on "Deploy API" button on the top left.
1. Under "Deployment Stage", click "New Stage".
1. Under "Stage Name", I will type in "prod".
1. Click "Deploy".
1. Note the "Invoke URL" at the top and your API is now live.

### Slack
1. Go to [Slack Apps](https://slack.com/apps).
1. Search for "Outgoing WebHooks".
1. Click "Install" besides the team you wanted.
1. Click "Add Outgoing WebHook Integration".
1. Scroll down to "Integration Settings" section.
1. Under "Channel", choose "Any".
1. Under "Trigger Word(s)", type in "nimbus" (without the quotes).
1. Under "URL(s)", type in your "Invoke URL" as noted above.
1. Customize "Descriptive Label", "Name" and "Icon" (you can use cloudy_robot_200.png from the nimbus repo) )to your liking and click "Save Settings".
1. Copy the Token value.
1. You are all set.

### Configuration data
1. Go to [Identity and Access Management](https://console.aws.amazon.com/iam/home?region=us-east-1#encryptionKeys/us-east-1)
1. Create the following mandatory keys - SlackAPIKey (Slack AP Token),  nimbus (Slack verification token)
1. Create optional keys - DigitalOcean (DigitalOcean API key), SoftLayer (user name and a token), Google
1. For each of the created keys do the following
    1. `aws kms encrypt --key-id alias/<KMS key name> --plaintext "<COMMAND_TOKEN>"`
1. Copy the base-64 encoded, encrypted key
1. if you you want to list your GCE instance, create keys as describe [here](https://developers.google.com/identity/protocols/application-default-credentials)
1. For each of the keys decrypt using
    1. `aws kms encrypt --key-id alias/NimbusGoogle --plaintext fileb://"key file"" --output text "`
1. Store tis values in a string set by the name of GCETokens in dynamodb.
1. Go to [DynamoDB](https://console.aws.amazon.com/dynamodb/home?region=us-east-1) and create a table by the name of nimbus
1. Add the following items to the table:
 1. BotName - Default "Nimbus"
 1. DigitalOcean - Encrypted DigitalOcean key
 1. SlackAPI - Encrypted SlackAPI Token
 1. SlackExpected - Encrypted Slack verification token
 1. SLUserName - SoftLayer user name
 1. SLAPI - SoftLayer API key
 1. icon - Url for the bot icon
1. Give your function's role permission for the kms:Decrypt action.
   Example:
  ```json   
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
     }```

### Ready, Set, Go!

You can deploy your code by running `apex deploy`
