import os
from botocore.exceptions import EndpointConnectionError, ClientError
from mat.aws.sns import get_aws_sns_client
import json
from dds.logs import lg_sns as lg


# todo > move this to webservice

def sns_serve(sqs_msg_dict):
    topic_arn = os.getenv('DDH_AWS_SNS_TOPIC_ARN')
    if topic_arn is None or ':' not in topic_arn:
        print('error: missing or bad topic ARN')
        return 1

    d = sqs_msg_dict
    s = '{} - {}'.format(d['reason'], d['vessel'])
    parsed_region = topic_arn.split(':')[3]
    long_s = json.dumps(sqs_msg_dict)

    try:
        cli = get_aws_sns_client(my_region=parsed_region)
        response = cli.publish(
            TargetArn=topic_arn,
            Message=json.dumps({'default': s,
                                'sms': s,
                                'email': long_s}),
            Subject=s,
            MessageStructure='json'
        )
        # response format very complicated, only use:
        if int(response['ResponseMetadata']['HTTPStatusCode']) == 200:
            lg.a('message published OK -> {}'.format(s))
            return 0
        return 2

    except (ClientError, EndpointConnectionError, Exception) as ex:
        print(ex)
        return 3
