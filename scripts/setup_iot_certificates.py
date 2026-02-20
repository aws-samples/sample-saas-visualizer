#!/usr/bin/env python3
# /// script
# requires-python = ">=3.13"
# dependencies = [
#   "boto3>=1.35.0",
# ]
# ///
"""
IoT Certificate Management Script for Visualise SaaS

This script generates and manages certificates for IoT devices that connect
to the Visualise SaaS backend. It must be run after CloudFormation stack
deployment is complete.

Usage:
    # Create certificates
    uv run scripts/setup_iot_certificates.py create
    uv run scripts/setup_iot_certificates.py create --stack-name visualise-saas --output-dir ./iot-certificates

    # Delete certificates
    uv run scripts/setup_iot_certificates.py delete
    uv run scripts/setup_iot_certificates.py delete --certificate-id abc123... --stack-name visualise-saas
"""

import argparse
import hashlib
import json
import logging
import os
import re
import shutil
import sys
import urllib.request
from pathlib import Path

import boto3
from botocore.exceptions import ClientError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Amazon Root CA 1 URL and SHA256 checksum
# Checksum verified 2024-12 from https://www.amazontrust.com/repository/
# If Amazon rotates the root CA, this will need updating
ROOT_CA_URL = "https://www.amazontrust.com/repository/AmazonRootCA1.pem"
ROOT_CA_SHA256 = "2c43952ee9e000ff2acc4e2ed0897c0a72ad5fa72c3d934e81741cbd54f05bd1"

__all__ = ['IoTCertificateManager']

# AWS IoT certificate ID is a 64-character hex string
CERT_ID_PATTERN = r'^[a-f0-9]{64}$'


class IoTCertificateManager:
    """Manages IoT certificates for device authentication."""

    def __init__(self, stack_name: str, region: str | None = None):
        """
        Initialize the IoT Certificate Manager.

        Args:
            stack_name: Name of the CloudFormation stack
            region: AWS region (defaults to AWS_DEFAULT_REGION env var, then eu-west-1)
        """
        self.stack_name = stack_name
        self.region = region or os.environ.get('AWS_DEFAULT_REGION', 'eu-west-1')

        logger.info(f"Initializing IoT Certificate Manager for stack '{stack_name}' in region '{self.region}'")

        try:
            self.cfn_client = boto3.client('cloudformation', region_name=self.region)
            self.iot_client = boto3.client('iot', region_name=self.region)
        except Exception as e:
            logger.error(f"Failed to initialize AWS clients: {e}")
            raise

    def get_stack_outputs(self) -> dict[str, str]:
        """
        Retrieve CloudFormation stack outputs.

        Returns:
            Dictionary mapping output keys to values

        Raises:
            Exception: If stack doesn't exist or is not in a complete state
        """
        logger.info(f"Retrieving stack outputs for '{self.stack_name}'...")

        try:
            response = self.cfn_client.describe_stacks(StackName=self.stack_name)
            stack = response['Stacks'][0]

            stack_status = stack['StackStatus']
            if stack_status not in ['CREATE_COMPLETE', 'UPDATE_COMPLETE']:
                raise Exception(
                    f"Stack is in '{stack_status}' state. "
                    f"Wait for deployment to complete before running this script."
                )

            outputs = {}
            for output in stack.get('Outputs', []):
                outputs[output['OutputKey']] = output['OutputValue']

            required_outputs = ['IoTThingName', 'IoTPolicyName', 'IoTTopicName']
            missing = [key for key in required_outputs if key not in outputs]

            if missing:
                raise Exception(
                    f"Missing required stack outputs: {', '.join(missing)}. "
                    f"Ensure your CloudFormation template includes these outputs."
                )

            logger.info("Successfully retrieved stack outputs")
            logger.info(f"  Thing Name: {outputs['IoTThingName']}")
            logger.info(f"  Policy Name: {outputs['IoTPolicyName']}")
            logger.info(f"  Topic Name: {outputs['IoTTopicName']}")

            return outputs

        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'ValidationError':
                logger.error(f"Stack '{self.stack_name}' not found in region '{self.region}'")
            else:
                logger.error(f"Failed to get stack outputs: {e}")
            raise

    def get_iot_endpoint(self) -> str:
        """
        Get the AWS IoT endpoint for device connections.

        Returns:
            IoT endpoint address (e.g., xyz.iot.eu-west-1.amazonaws.com)
        """
        logger.info("Retrieving IoT endpoint...")

        try:
            response = self.iot_client.describe_endpoint(endpointType='iot:Data-ATS')
            endpoint = response['endpointAddress']
            logger.info(f"  IoT Endpoint: {endpoint}")
            return endpoint
        except ClientError as e:
            logger.error(f"Failed to get IoT endpoint: {e}")
            raise

    def create_certificate(self) -> dict[str, str]:
        """
        Create keys and certificate using AWS IoT.

        Returns:
            Dictionary containing certificate data:
            - certificateArn
            - certificateId
            - certificatePem
            - keyPair (publicKey, privateKey)
        """
        logger.info("Creating new IoT certificate and keys...")

        try:
            response = self.iot_client.create_keys_and_certificate(setAsActive=True)

            cert_data = {
                'certificateArn': response['certificateArn'],
                'certificateId': response['certificateId'],
                'certificatePem': response['certificatePem'],
                'publicKey': response['keyPair']['PublicKey'],
                'privateKey': response['keyPair']['PrivateKey']
            }

            logger.info(f"  Certificate ARN: {cert_data['certificateArn']}")
            logger.info(f"  Certificate ID: {cert_data['certificateId']}")
            logger.info("  Certificate activated successfully")

            return cert_data

        except ClientError as e:
            logger.error(f"Failed to create certificate: {e}")
            raise

    def attach_policy_to_certificate(self, certificate_arn: str, policy_name: str):
        """
        Attach IoT policy to certificate.

        Args:
            certificate_arn: ARN of the certificate
            policy_name: Name of the IoT policy
        """
        logger.info(f"Attaching policy '{policy_name}' to certificate...")

        try:
            self.iot_client.attach_policy(
                policyName=policy_name,
                target=certificate_arn
            )
            logger.info("  Policy attached successfully")
        except ClientError as e:
            logger.error(f"Failed to attach policy: {e}")
            raise

    def attach_certificate_to_thing(self, certificate_arn: str, thing_name: str):
        """
        Attach certificate to IoT Thing.

        Args:
            certificate_arn: ARN of the certificate
            thing_name: Name of the IoT Thing
        """
        logger.info(f"Attaching certificate to Thing '{thing_name}'...")

        try:
            self.iot_client.attach_thing_principal(
                thingName=thing_name,
                principal=certificate_arn
            )
            logger.info("  Certificate attached to Thing successfully")
        except ClientError as e:
            logger.error(f"Failed to attach certificate to Thing: {e}")
            raise

    def detach_policy_from_certificate(self, certificate_arn: str, policy_name: str):
        """
        Detach IoT policy from certificate.

        Args:
            certificate_arn: ARN of the certificate
            policy_name: Name of the IoT policy
        """
        logger.info(f"Detaching policy '{policy_name}' from certificate...")

        try:
            self.iot_client.detach_policy(
                policyName=policy_name,
                target=certificate_arn
            )
            logger.info("  Policy detached successfully")
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'ResourceNotFoundException':
                logger.warning(f"  Policy already detached or not found")
            else:
                logger.error(f"Failed to detach policy: {e}")
                raise

    def detach_certificate_from_thing(self, certificate_arn: str, thing_name: str):
        """
        Detach certificate from IoT Thing.

        Args:
            certificate_arn: ARN of the certificate
            thing_name: Name of the IoT Thing
        """
        logger.info(f"Detaching certificate from Thing '{thing_name}'...")

        try:
            self.iot_client.detach_thing_principal(
                thingName=thing_name,
                principal=certificate_arn
            )
            logger.info("  Certificate detached from Thing successfully")
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'ResourceNotFoundException':
                logger.warning(f"  Certificate already detached or not found")
            else:
                logger.error(f"Failed to detach certificate from Thing: {e}")
                raise

    def update_certificate_status(self, certificate_id: str, status: str):
        """
        Update certificate status (ACTIVE or INACTIVE).

        Args:
            certificate_id: ID of the certificate
            status: New status (ACTIVE or INACTIVE)
        """
        logger.info(f"Updating certificate status to {status}...")

        try:
            self.iot_client.update_certificate(
                certificateId=certificate_id,
                newStatus=status
            )
            logger.info(f"  Certificate status updated to {status}")
        except ClientError as e:
            logger.error(f"Failed to update certificate status: {e}")
            raise

    def delete_certificate(self, certificate_id: str):
        """
        Delete certificate from AWS IoT.

        Args:
            certificate_id: ID of the certificate
        """
        logger.info(f"Deleting certificate {certificate_id}...")

        try:
            self.iot_client.delete_certificate(certificateId=certificate_id)
            logger.info("  Certificate deleted successfully")
        except ClientError as e:
            logger.error(f"Failed to delete certificate: {e}")
            raise

    def list_thing_certificates(self, thing_name: str) -> list[str]:
        """
        List all certificates attached to a Thing.

        Args:
            thing_name: Name of the IoT Thing

        Returns:
            List of certificate ARNs
        """
        logger.info(f"Listing certificates for Thing '{thing_name}'...")

        try:
            principals = []
            paginator = self.iot_client.get_paginator('list_thing_principals')
            for page in paginator.paginate(thingName=thing_name):
                principals.extend(page.get('principals', []))

            # Filter for certificate ARNs (not other principal types)
            cert_arns = [p for p in principals if ':cert/' in p]

            if cert_arns:
                logger.info(f"  Found {len(cert_arns)} certificate(s)")
                for arn in cert_arns:
                    logger.info(f"    - {arn}")
            else:
                logger.info("  No certificates found")

            return cert_arns

        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'ResourceNotFoundException':
                logger.warning(f"  Thing '{thing_name}' not found")
                return []
            else:
                logger.error(f"Failed to list Thing certificates: {e}")
                raise

    def download_root_ca(self, output_dir: Path) -> Path:
        """
        Download Amazon Root CA certificate with checksum verification.

        Args:
            output_dir: Directory to save the Root CA file

        Returns:
            Path to the downloaded Root CA file
        """
        logger.info("Downloading Amazon Root CA certificate...")

        # Ensure output directory exists
        output_dir.mkdir(parents=True, exist_ok=True)

        root_ca_path = output_dir / "rootCA.pem"

        try:
            with urllib.request.urlopen(ROOT_CA_URL, timeout=30) as response:
                content = response.read()

            # Verify checksum
            actual_hash = hashlib.sha256(content).hexdigest()
            if actual_hash != ROOT_CA_SHA256:
                raise ValueError(
                    f"Root CA checksum mismatch. Expected {ROOT_CA_SHA256}, got {actual_hash}"
                )

            root_ca_path.write_bytes(content)
            logger.info(f"  Root CA saved to: {root_ca_path}")
            logger.info("  Checksum verified successfully")
            return root_ca_path
        except Exception as e:
            logger.error(f"Failed to download Root CA: {e}")
            raise

    def save_certificates(
        self,
        cert_data: dict[str, str],
        output_dir: Path,
        endpoint: str,
        thing_name: str,
        topic_name: str
    ):
        """
        Save certificate files to local directory.

        Args:
            cert_data: Certificate data from create_certificate()
            output_dir: Directory to save certificate files
            endpoint: IoT endpoint address
            thing_name: Name of the IoT Thing
            topic_name: Name of the IoT topic
        """
        logger.info(f"Saving certificate files to: {output_dir}")

        # Create output directory if it doesn't exist
        output_dir.mkdir(parents=True, exist_ok=True)

        # Save certificate
        cert_file = output_dir / "certificate.pem.crt"
        cert_file.write_text(cert_data['certificatePem'])
        logger.info(f"  Saved: {cert_file}")

        # Save private key with restrictive permissions
        private_key_file = output_dir / "private.pem.key"
        private_key_file.write_text(cert_data['privateKey'])
        os.chmod(private_key_file, 0o600)
        logger.info(f"  Saved: {private_key_file} (permissions: 600)")

        # Save public key
        public_key_file = output_dir / "public.pem.key"
        public_key_file.write_text(cert_data['publicKey'])
        logger.info(f"  Saved: {public_key_file}")

        # Create device configuration file
        # Note: client_id is set to thing_name as AWS IoT best practice for 1:1 mapping
        device_config = {
            "endpoint": endpoint,
            "thing_name": thing_name,
            "topic": topic_name,
            "certificate_arn": cert_data['certificateArn'],
            "certificate_id": cert_data['certificateId'],
            "region": self.region,
            "client_id": thing_name,
            "paths": {
                "certificate": str(cert_file.name),
                "private_key": str(private_key_file.name),
                "root_ca": "rootCA.pem"
            }
        }

        config_file = output_dir / "device-config.json"
        config_file.write_text(json.dumps(device_config, indent=2))
        logger.info(f"  Saved: {config_file}")

    def setup(self, output_dir: Path | None = None, force: bool = False) -> dict[str, str]:
        """
        Execute complete certificate setup workflow.

        Args:
            output_dir: Directory to save certificate files (default: ./iot-certificates)
            force: If True, overwrite existing certificate files

        Returns:
            Dictionary with setup information
        """
        if output_dir is None:
            output_dir = Path('./iot-certificates')

        # Check if output directory exists and contains files
        if output_dir.exists() and any(output_dir.iterdir()) and not force:
            raise FileExistsError(
                f"Output directory '{output_dir}' already exists and contains files. "
                f"Use --force to overwrite."
            )

        logger.info("=" * 60)
        logger.info("Starting IoT Certificate Setup")
        logger.info("=" * 60)

        # Step 1: Get stack outputs
        outputs = self.get_stack_outputs()
        thing_name = outputs['IoTThingName']
        policy_name = outputs['IoTPolicyName']
        topic_name = outputs['IoTTopicName']

        # Step 2: Get IoT endpoint
        endpoint = self.get_iot_endpoint()

        # Step 3: Create certificate
        cert_data = self.create_certificate()

        # Step 4: Attach policy to certificate
        self.attach_policy_to_certificate(cert_data['certificateArn'], policy_name)

        # Step 5: Attach certificate to Thing
        self.attach_certificate_to_thing(cert_data['certificateArn'], thing_name)

        # Step 6: Download Root CA
        self.download_root_ca(output_dir)

        # Step 7: Save certificate files
        self.save_certificates(cert_data, output_dir, endpoint, thing_name, topic_name)

        logger.info("=" * 60)
        logger.info("Certificate Setup Complete!")
        logger.info("=" * 60)
        logger.info(f"\nCertificate files saved to: {output_dir.absolute()}")
        logger.info("\nNext steps:")
        logger.info("1. Copy certificate files to your IoT device")
        logger.info(f"   scp -r {output_dir}/* pi@raspberrypi.local:/home/pi/iot-certificates/")
        logger.info("2. Update device configuration with values from device-config.json")
        logger.info("3. Test device connection to IoT Core")

        return {
            'endpoint': endpoint,
            'thing_name': thing_name,
            'topic_name': topic_name,
            'certificate_arn': cert_data['certificateArn'],
            'certificate_id': cert_data['certificateId'],
            'output_dir': str(output_dir.absolute())
        }

    def cleanup(
        self,
        certificate_id: str | None = None,
        output_dir: Path | None = None,
        delete_files: bool = False,
        dry_run: bool = False
    ):
        """
        Clean up certificate resources from AWS IoT.

        Args:
            certificate_id: Specific certificate ID to delete (if None, deletes all from Thing)
            output_dir: Directory containing certificate files (required if delete_files=True)
            delete_files: If True, also delete local certificate files
            dry_run: If True, preview what would be deleted without making changes

        Raises:
            Exception: If any certificate cleanup fails partially
        """
        if dry_run:
            logger.info("=" * 60)
            logger.info("DRY RUN - No changes will be made")
            logger.info("=" * 60)

        logger.info("=" * 60)
        logger.info("Starting IoT Certificate Cleanup")
        logger.info("=" * 60)

        # Step 1: Get stack outputs
        outputs = self.get_stack_outputs()
        thing_name = outputs['IoTThingName']
        policy_name = outputs['IoTPolicyName']

        # Step 2: Determine which certificates to delete
        if certificate_id:
            # Use specified certificate ID
            cert_id = certificate_id
            # Extract cert ID from ARN if full ARN was provided
            if ':cert/' in cert_id:
                cert_id = cert_id.split(':cert/')[-1]

            # Validate certificate ID format (64-character hex string)
            if not re.match(CERT_ID_PATTERN, cert_id):
                raise ValueError(
                    f"Invalid certificate ID format: '{cert_id}'. "
                    f"Expected 64-character hex string."
                )

            # Get AWS account ID
            sts_client = boto3.client('sts', region_name=self.region)
            account_id = sts_client.get_caller_identity()['Account']

            cert_arn = f"arn:aws:iot:{self.region}:{account_id}:cert/{cert_id}"
            cert_ids_to_delete = [cert_id]
            cert_arns_to_detach = [cert_arn]

            logger.info(f"Deleting specific certificate: {cert_id}")
        else:
            # Delete all certificates attached to the Thing
            logger.info("No certificate ID specified, will delete all certificates attached to Thing")
            cert_arns_to_detach = self.list_thing_certificates(thing_name)

            if not cert_arns_to_detach:
                logger.warning("No certificates found to delete")

                # Check if we should delete local files anyway
                if delete_files and output_dir and output_dir.exists():
                    self._delete_local_files(output_dir)

                logger.info("=" * 60)
                logger.info("Cleanup Complete (nothing to delete)")
                logger.info("=" * 60)
                return

            cert_ids_to_delete = [arn.split(':cert/')[-1] for arn in cert_arns_to_detach]

        # Step 3: Process each certificate
        failed_certs = []
        for cert_arn, cert_id in zip(cert_arns_to_detach, cert_ids_to_delete):
            logger.info(f"\nProcessing certificate: {cert_id}")

            if dry_run:
                logger.info(f"  Would detach from Thing '{thing_name}'")
                logger.info(f"  Would detach policy '{policy_name}'")
                logger.info("  Would set status to INACTIVE")
                logger.info("  Would delete certificate")
            else:
                try:
                    # Detach from Thing
                    self.detach_certificate_from_thing(cert_arn, thing_name)

                    # Detach policy
                    self.detach_policy_from_certificate(cert_arn, policy_name)

                    # Update to INACTIVE (required before deletion)
                    self.update_certificate_status(cert_id, 'INACTIVE')

                    # Delete certificate
                    self.delete_certificate(cert_id)
                except Exception as e:
                    logger.error(f"Failed to fully clean up certificate {cert_id}: {e}")
                    failed_certs.append(cert_id)

        # Step 4: Delete local files if requested
        if delete_files and output_dir:
            if dry_run:
                logger.info(f"\nWould delete local files from: {output_dir}")
            else:
                self._delete_local_files(output_dir)

        if failed_certs:
            raise Exception(f"Failed to clean up {len(failed_certs)} certificate(s): {', '.join(failed_certs)}")

        logger.info("\n" + "=" * 60)
        if dry_run:
            logger.info("DRY RUN Complete - No changes were made")
        else:
            logger.info("Cleanup Complete!")
        logger.info("=" * 60)
        action = "Would delete" if dry_run else "Deleted"
        logger.info(f"\n{action} {len(cert_ids_to_delete)} certificate(s) from AWS IoT")
        if delete_files and output_dir:
            logger.info(f"{action} local certificate files from: {output_dir}")

    def _delete_local_files(self, output_dir: Path):
        """
        Delete local certificate files.

        Args:
            output_dir: Directory containing certificate files
        """
        if not output_dir.exists():
            logger.info(f"Output directory '{output_dir}' does not exist, skipping file deletion")
            return

        logger.info(f"Deleting local certificate files from: {output_dir}")

        try:
            shutil.rmtree(output_dir)
            logger.info(f"  Successfully deleted directory: {output_dir}")
        except Exception as e:
            logger.error(f"  Failed to delete directory: {e}")
            raise


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description='Generate and manage IoT certificates for Visualise SaaS devices',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Create certificates (using defaults)
  uv run scripts/setup_iot_certificates.py create

  # Create with custom options
  uv run scripts/setup_iot_certificates.py create --stack-name my-stack --output-dir ./certs --force

  # Delete specific certificate
  uv run scripts/setup_iot_certificates.py delete --certificate-id abc123...

  # Delete all certificates for the Thing
  uv run scripts/setup_iot_certificates.py delete

  # Preview what would be deleted (dry run)
  uv run scripts/setup_iot_certificates.py delete --dry-run

  # Delete certificates and local files
  uv run scripts/setup_iot_certificates.py delete --delete-files --output-dir ./iot-certificates

  # Delete using certificate ID from device-config.json
  uv run scripts/setup_iot_certificates.py delete --from-config ./iot-certificates/device-config.json
"""
    )

    # Add subcommands
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    subparsers.required = True

    # Create command
    create_parser = subparsers.add_parser('create', help='Create new IoT certificate')
    create_parser.add_argument(
        '--stack-name',
        default='visualise-saas',
        help='CloudFormation stack name (default: visualise-saas)'
    )
    create_parser.add_argument(
        '--output-dir',
        default='./iot-certificates',
        help='Directory to save certificate files (default: ./iot-certificates)'
    )
    create_parser.add_argument(
        '--region',
        help='AWS region (default: AWS_DEFAULT_REGION or eu-west-1)'
    )
    create_parser.add_argument(
        '--force',
        action='store_true',
        help='Force overwrite existing certificate files'
    )

    # Delete command
    delete_parser = subparsers.add_parser('delete', help='Delete IoT certificate')
    delete_parser.add_argument(
        '--stack-name',
        default='visualise-saas',
        help='CloudFormation stack name (default: visualise-saas)'
    )
    cert_id_group = delete_parser.add_mutually_exclusive_group()
    cert_id_group.add_argument(
        '--certificate-id',
        help='Certificate ID or ARN to delete (if not specified, deletes all certificates for Thing)'
    )
    cert_id_group.add_argument(
        '--from-config',
        type=Path,
        help='Read certificate ID from device-config.json file'
    )
    delete_parser.add_argument(
        '--output-dir',
        default='./iot-certificates',
        help='Directory containing certificate files (default: ./iot-certificates)'
    )
    delete_parser.add_argument(
        '--delete-files',
        action='store_true',
        help='Also delete local certificate files'
    )
    delete_parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview what would be deleted without making changes'
    )
    delete_parser.add_argument(
        '--region',
        help='AWS region (default: AWS_DEFAULT_REGION or eu-west-1)'
    )

    args = parser.parse_args()

    try:
        # Initialize certificate manager
        manager = IoTCertificateManager(
            stack_name=args.stack_name,
            region=args.region
        )

        if args.command == 'create':
            # Execute create workflow
            output_dir = Path(args.output_dir)
            manager.setup(output_dir, force=args.force)
            sys.exit(0)

        elif args.command == 'delete':
            # Determine certificate ID
            certificate_id = args.certificate_id

            if args.from_config:
                # Read certificate ID from config file
                if not args.from_config.exists():
                    logger.error(f"Config file not found: {args.from_config}")
                    sys.exit(1)

                try:
                    config = json.loads(args.from_config.read_text())
                    certificate_id = config.get('certificate_id')
                    if not certificate_id:
                        logger.error("certificate_id not found in config file")
                        sys.exit(1)
                    logger.info(f"Read certificate ID from config: {certificate_id}")
                except Exception as e:
                    logger.error(f"Failed to read config file: {e}")
                    sys.exit(1)

            # Execute delete workflow
            output_dir = Path(args.output_dir) if args.delete_files else None
            manager.cleanup(
                certificate_id=certificate_id,
                output_dir=output_dir,
                delete_files=args.delete_files,
                dry_run=args.dry_run
            )
            sys.exit(0)

    except KeyboardInterrupt:
        logger.info("\nOperation cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\nOperation failed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
