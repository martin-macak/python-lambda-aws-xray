# AWS Lambda X-Ray Instrumentation Layer

A lightweight AWS Lambda layer that automatically instruments Python code with AWS X-Ray tracing. This layer provides zero-configuration X-Ray instrumentation by leveraging Python's `sitecustomize.py` mechanism to automatically patch common AWS services and libraries.

## Architecture Overview

This layer implements automatic X-Ray instrumentation through a three-component architecture:

1. **Bootstrap Script** (`aws_lambda_layer/bin/bootstrap`)
   - Modifies the Python runtime environment to include the layer's packages
   - Sets `USER_SITE` and `ENABLE_USER_SITE` environment variables
   - Enables Python to automatically import `sitecustomize.py` from `/opt/bin/python`

2. **Site Customization** (`aws_lambda_layer/bin/python/sitecustomize.py`)
   - Automatically executed when Python interpreter starts
   - Performs dependency checks and version validation
   - Applies AWS X-Ray patching to supported libraries

3. **Minimal Dependencies** (Built via Makefile)
   - Includes only `aws-xray-sdk` and `wrapt` packages
   - Relies on Lambda runtime to provide `botocore` (>=1.11.3)
   - Creates the smallest possible layer size

## How It Works

### AWS_LAMBDA_EXEC_WRAPPER Integration

The layer uses AWS Lambda's `AWS_LAMBDA_EXEC_WRAPPER` environment variable to intercept the runtime startup process. When you set:

```bash
AWS_LAMBDA_EXEC_WRAPPER=/opt/bin/bootstrap
```

Lambda will execute the bootstrap script before starting your function, allowing the layer to modify the runtime environment.

### Runtime Modification

The bootstrap script modifies the Lambda runtime environment by:

```bash
# Bootstrap script sets environment variables
export USER_SITE="/opt/bin/python"
export ENABLE_USER_SITE="1"
```

This causes Python to automatically import `sitecustomize.py` from the layer's Python path, triggering instrumentation before your Lambda function code runs.

### Automatic Instrumentation

The `sitecustomize.py` module performs the following steps:

1. **Dependency Check**: Verifies `botocore` is available in the Lambda runtime
2. **Version Validation**: Ensures `botocore` version meets minimum requirement (>=1.11.3)
3. **X-Ray Patching**: Applies instrumentation to boto3, botocore, requests, and other supported libraries

```python
from aws_xray_sdk.core import patch_all
patch_all(double_patch=True)
```

### Layer Size Optimization

The layer is optimized for minimal size by:

- **Excluding botocore**: Lambda runtime provides botocore>=1.11.3, so it's not included
- **Including only essentials**: Only `aws-xray-sdk` and `wrapt` packages are bundled
- **Version checking**: Runtime validation ensures compatibility without bundling older versions

## Dependencies

### Required by AWS X-Ray SDK

According to the [AWS X-Ray SDK for Python](https://github.com/aws/aws-xray-sdk-python), the following dependencies are required:

- `botocore >= 1.11.3` (provided by Lambda runtime)
- `wrapt` (included in layer)

### Layer Dependencies

The layer includes only the minimal required packages:

```toml
[project]
dependencies = [
    "aws-xray-sdk>=2.14.0",
    "wrapt>=1.17.2",
]
```

## Building the Layer

### Prerequisites

- Python 3.13+
- `uv` package manager
- `jq` command-line JSON processor
- `toml2json` utility

### Build Process

```bash
# Build the layer
make

# Clean build artifacts
make clean
```

The Makefile performs the following steps:

1. **Copy source files**: Copies bootstrap script and sitecustomize.py
2. **Download dependencies**: Downloads only aws-xray-sdk and wrapt packages
3. **Extract packages**: Extracts to `/opt/bin/python` for runtime access
4. **Create layer zip**: Packages everything into `dist/layer.zip`

## Usage

### Deploy the Layer

1. Build the layer:
   ```bash
   make
   ```

2. Deploy using AWS CLI:
   ```bash
   aws lambda publish-layer-version \
     --layer-name python-xray-instrumentation \
     --zip-file fileb://dist/layer.zip \
     --compatible-runtimes python3.9 python3.10 python3.11 python3.12 python3.13
   ```

### Apply to Lambda Function

#### Method 1: Using AWS_LAMBDA_EXEC_WRAPPER (Recommended)

Add the layer and set the execution wrapper environment variable:

```bash
# Add the layer
aws lambda update-function-configuration \
  --function-name my-function \
  --layers arn:aws:lambda:region:account:layer:python-xray-instrumentation:1

# Set the execution wrapper to use the layer's bootstrap script
aws lambda update-function-configuration \
  --function-name my-function \
  --environment Variables='{AWS_LAMBDA_EXEC_WRAPPER=/opt/bin/bootstrap}'
```

#### Method 2: Using AWS SAM Template

```yaml
Resources:
  MyFunction:
    Type: AWS::Serverless::Function
    Properties:
      CodeUri: src/
      Handler: app.lambda_handler
      Runtime: python3.11
      Environment:
        Variables:
          AWS_LAMBDA_EXEC_WRAPPER: /opt/bin/bootstrap
      Layers:
        - !Ref XRayInstrumentationLayer
        
  XRayInstrumentationLayer:
    Type: AWS::Serverless::LayerVersion
    Properties:
      LayerName: python-xray-instrumentation
      ContentUri: dist/layer.zip
      CompatibleRuntimes:
        - python3.9
        - python3.10
        - python3.11
        - python3.12
        - python3.13
```

#### Method 3: Using AWS CDK (TypeScript)

```typescript
import * as lambda from 'aws-cdk-lib/aws-lambda';

const layer = new lambda.LayerVersion(this, 'XRayInstrumentationLayer', {
  code: lambda.Code.fromAsset('dist/layer.zip'),
  compatibleRuntimes: [
    lambda.Runtime.PYTHON_3_9,
    lambda.Runtime.PYTHON_3_10,
    lambda.Runtime.PYTHON_3_11,
    lambda.Runtime.PYTHON_3_12,
    lambda.Runtime.PYTHON_3_13,
  ],
});

const lambdaFunction = new lambda.Function(this, 'MyFunction', {
  runtime: lambda.Runtime.PYTHON_3_11,
  handler: 'app.lambda_handler',
  code: lambda.Code.fromAsset('src'),
  layers: [layer],
  environment: {
    AWS_LAMBDA_EXEC_WRAPPER: '/opt/bin/bootstrap',
  },
});
```

#### Method 4: Using Terraform

```hcl
resource "aws_lambda_layer_version" "xray_instrumentation" {
  filename         = "dist/layer.zip"
  layer_name       = "python-xray-instrumentation"
  source_code_hash = filebase64sha256("dist/layer.zip")
  
  compatible_runtimes = [
    "python3.9",
    "python3.10", 
    "python3.11",
    "python3.12",
    "python3.13"
  ]
}

resource "aws_lambda_function" "my_function" {
  filename         = "my-function.zip"
  function_name    = "my-function"
  role            = aws_iam_role.lambda_role.arn
  handler         = "app.lambda_handler"
  runtime         = "python3.11"
  
  layers = [aws_lambda_layer_version.xray_instrumentation.arn]
  
  environment {
    variables = {
      AWS_LAMBDA_EXEC_WRAPPER = "/opt/bin/bootstrap"
    }
  }
}
```

### Enable X-Ray Tracing

Enable X-Ray tracing on your Lambda function:

```bash
aws lambda update-function-configuration \
  --function-name my-function \
  --tracing-config Mode=Active
```

## Design Decisions

### Why AWS_LAMBDA_EXEC_WRAPPER?

`AWS_LAMBDA_EXEC_WRAPPER` is the standard mechanism for Lambda runtime extensions. It allows the layer to:

- **Intercept startup**: Execute before the Python interpreter starts
- **Modify environment**: Set environment variables that affect Python's module loading
- **Zero configuration**: Works automatically without code changes
- **Lambda native**: Uses official AWS Lambda functionality

### Why sitecustomize.py?

Python automatically imports `sitecustomize.py` if it exists in the site-packages directory. This provides a clean way to perform initialization without modifying user code.

### Why exclude botocore?

- **Runtime provided**: Lambda runtime already includes botocore>=1.11.3
- **Size optimization**: Excluding botocore significantly reduces layer size
- **Version flexibility**: Runtime botocore versions are kept up-to-date by AWS

### Why bootstrap script?

The bootstrap script ensures the layer's Python packages are available in the module search path by modifying environment variables before the Python interpreter starts.

## Troubleshooting

### Common Issues

1. **Instrumentation not working**: 
   - Verify `AWS_LAMBDA_EXEC_WRAPPER=/opt/bin/bootstrap` is set
   - Check Lambda function logs for warnings from `python-lambda-aws-xray` logger
   - Ensure X-Ray tracing is enabled on the function

2. **Version conflicts**: Ensure Lambda runtime has botocore>=1.11.3

3. **Layer size**: Layer should be <10MB due to minimal dependencies

4. **Bootstrap script not executing**:
   - Confirm `AWS_LAMBDA_EXEC_WRAPPER` environment variable is properly set
   - Check that the layer is attached to the Lambda function
   - Verify the bootstrap script has execute permissions

### Debug Logging

The layer logs instrumentation status at INFO level:

```
[INFO] AWS X-Ray instrumentation successfully applied.
```

And warnings for any issues:

```
[WARNING] botocore version X.Y.Z is less than required 1.11.3. Skipping AWS X-Ray instrumentation.
```

## File Structure

```
aws_lambda_layer/
   bin/
      bootstrap              # Runtime environment setup
      python/
          sitecustomize.py   # Auto-instrumentation logic
   build/                     # Build artifacts (generated)
   dist/                      # Layer distribution (generated)
   Makefile                   # Build automation
   pyproject.toml             # Project dependencies
   README.md                  # This documentation
```

## License

This project is designed for AWS Lambda X-Ray instrumentation and follows AWS best practices for layer development.