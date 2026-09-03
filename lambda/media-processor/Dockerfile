# SentinelVision Media Processor
#
# AWS Lambda container image for automated image/video processing.
# OpenCV is installed inside the container so the Lambda function can
# perform computer-vision metadata extraction on uploaded media.

# ---------------------------------------------------------------------------
# AWS Lambda Python runtime
# ---------------------------------------------------------------------------

FROM public.ecr.aws/lambda/python:3.12


# ---------------------------------------------------------------------------
# Install Linux libraries required by OpenCV
# ---------------------------------------------------------------------------

RUN dnf install -y \
    mesa-libGL \
    && dnf clean all


# ---------------------------------------------------------------------------
# Install Python dependencies
# ---------------------------------------------------------------------------

# opencv-python-headless is appropriate for server environments because
# Lambda does not need GUI/display functionality.

RUN pip install --no-cache-dir \
    opencv-python-headless \
    boto3


# ---------------------------------------------------------------------------
# Copy Lambda application code
# ---------------------------------------------------------------------------

COPY lambda_function.py ${LAMBDA_TASK_ROOT}/lambda_function.py


# ---------------------------------------------------------------------------
# Lambda entry point
# ---------------------------------------------------------------------------

CMD ["lambda_function.lambda_handler"]

