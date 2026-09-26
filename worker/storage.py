import os


def upload(path, key):
    import boto3

    client = boto3.client(
        "s3",
        endpoint_url=os.environ["R2_ENDPOINT"],
        aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
        region_name="auto",
    )
    client.upload_file(
        str(path),
        os.environ["R2_BUCKET"],
        "runs/" + key + ".wav",
        ExtraArgs={"ContentType": "audio/wav"},
    )
