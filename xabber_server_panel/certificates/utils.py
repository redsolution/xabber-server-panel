#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Automated Certificate Manager using ACME
# Copyright (c) Markus Hauschild & David Klaftenegger, 2016.
# Copyright (c) Rudolf Mayerhofer, 2019.
# available under the ISC license, see LICENSE

from acertmgr import tools, cert_revoke, cert_put
from acertmgr.tools import log, LOG_REPLACEMENTS
from acertmgr.tools import idna_convert
from acertmgr.configuration import parse_config_entry, parse_authority
from acertmgr.authority import authority
from . import challenge_handler
from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from datetime import datetime

from django.conf import settings
from django.template.loader import render_to_string
from django.utils.timezone import make_aware

from xabber_server_panel.base_modules.config.models import VirtualHost
from xabber_server_panel.certificates.models import Certificate

import os
import subprocess
import json
import io
import stat

try:
    import pwd
    import grp
except ImportError:
    # Warnings will be reported upon usage below
    pass


# @brief fetch new certificate from letsencrypt
# @param settings the domain's configuration options
def cert_get(settings):
    log("Getting certificate for %s" % settings['domainlist'])

    acme = authority(settings['authority'])
    acme.register_account()

    # create challenge handlers for this certificate
    challenge_handlers = dict()
    for domain in settings['domainlist']:
        # Create the challenge handler
        challenge_handlers[domain] = challenge_handler(settings['handlers'][domain])

    # create ssl key
    key_file = settings['key_file']
    if os.path.isfile(key_file):
        key = tools.read_pem_file(key_file, key=True)
    else:
        log("SSL key not found at '{0}'. Creating key.".format(key_file))
        key = tools.new_ssl_key(key_file, settings['key_algorithm'], settings['key_length'])

    # create ssl csr
    csr_file = settings['csr_file']
    if os.path.isfile(csr_file) and str(settings['csr_static']).lower() == 'true':
        log('Loading CSR from {}'.format(csr_file))
        cr = tools.read_pem_file(csr_file, csr=True)
    else:
        log('Generating CSR for {}'.format(settings['domainlist']))
        must_staple = str(settings.get('cert_must_staple')).lower() == "true"
        cr = tools.new_cert_request(settings['domainlist'], key, must_staple)
        tools.write_pem_file(cr, csr_file)

    # request cert with csr
    crt, ca = acme.get_crt_from_csr(cr, settings['domainlist'], challenge_handlers)

    #  if resulting certificate is valid: store in final location
    if tools.is_cert_valid(crt, settings['ttl_days']):
        log("Certificate '{}' renewed and valid until {}".format(tools.get_cert_cn(crt),
                                                                 tools.get_cert_valid_until(crt)))
        tools.write_pem_file(crt, settings['cert_file'], stat.S_IREAD)
        if (not str(settings.get('ca_static')).lower() == 'true' or not os.path.exists(settings['ca_file'])) \
                and ca is not None:
            tools.write_pem_file(ca, settings['ca_file'])

    return crt


def load(
        authority_tos_agreement='',
        force_renew='',
        revoke='',
        revoke_reason=''
    ):

    """ Customized for using in django """

    runtimeconfig = dict()

    domain_config_dir = work_dir = settings.CERT_CONF_DIR

    global_config_file = os.path.join(work_dir, settings.CERT_CONF_FILENAME)

    # Runtime configuration: Get from command-line options
    # - work_dir
    if work_dir:
        runtimeconfig['work_dir'] = work_dir
    else:
        runtimeconfig['work_dir'] = domain_config_dir
    #  create work_dir if it does not exist yet
    if not os.path.isdir(runtimeconfig['work_dir']):
        os.mkdir(runtimeconfig['work_dir'], int("0700", 8))

    # - authority_tos_agreement
    if authority_tos_agreement:
        runtimeconfig['authority_tos_agreement'] = authority_tos_agreement
    else:
        runtimeconfig['authority_tos_agreement'] = None

    # - force-rewew
    if force_renew:
        domaintranslation = [idna_convert(d) for d in force_renew.split(' ')]
        if len(domaintranslation) > 0:
            runtimeconfig['force_renew'] = domaintranslation
        else:
            runtimeconfig['force_renew'] = force_renew.split(' ')

    # - revoke
    if revoke:
        runtimeconfig['mode'] = 'revoke'
        runtimeconfig['revoke'] = revoke
        runtimeconfig['revoke_reason'] = revoke_reason

    # Global configuration: Load from file
    globalconfig = dict()
    if os.path.isfile(global_config_file):
        with io.open(global_config_file) as config_fd:
            try:
                globalconfig = json.load(config_fd)
            except ValueError:
                import yaml
                config_fd.seek(0)
                globalconfig = yaml.safe_load(config_fd)

    # Domain configuration(s): Load from file(s)
    domainconfigs = list()
    if os.path.isdir(domain_config_dir):
        for domain_config_file in os.listdir(domain_config_dir):
            domain_config_file = os.path.join(domain_config_dir, domain_config_file)
            # check file extension and skip if global config file
            if domain_config_file.endswith(".conf") and \
                    os.path.abspath(domain_config_file) != os.path.abspath(global_config_file):
                with io.open(domain_config_file) as config_fd:
                    try:
                        data = json.load(config_fd)
                    except ValueError:
                        import yaml
                        config_fd.seek(0)
                        data = yaml.safe_load(config_fd)
                    if isinstance(data, list):
                        # Handle newer config in list format (allows for multiple entries with same domains)
                        entries = list()
                        for element in data:
                            entries += element.items()
                    else:
                        # Handle older config format with just one entry per same domain set
                        entries = data.items()
                    for entry in entries:

                        # set crt folder path
                        if entry:
                            try:
                                domains = entry[0].split(' ')
                                domain = domains[0]
                                certs_dir = os.path.join(runtimeconfig.get('work_dir'), domain)
                                if not os.path.exists(certs_dir):
                                    os.mkdir(certs_dir)
                                runtimeconfig['work_dir'] = certs_dir
                            except Exception as e:
                                print(e)

                        domainconfigs.append(parse_config_entry(entry, globalconfig, runtimeconfig))

    # Define a fallback authority from global configuration / defaults
    runtimeconfig['fallback_authority'] = parse_authority([], globalconfig, runtimeconfig)

    return runtimeconfig, domainconfigs


def main(
        authority_tos_agreement='',
        force_renew='',
        revoke='',
        revoke_reason=''
    ):

    """ Customized for using in django """

    # update config
    update_cert_config()

    # load config
    runtimeconfig, domainconfigs = load(authority_tos_agreement, force_renew, revoke, revoke_reason)
    # register idna-mapped domains as LOG_REPLACEMENTS for better readability of log output
    for domainconfig in domainconfigs:
        LOG_REPLACEMENTS.update({k: "{} [{}]".format(k, v) for k, v in domainconfig['domainlist_idna_mapped'].items()})
    # Start processing
    if runtimeconfig.get('mode') == 'revoke':
        # Mode: revoke certificate
        log("Revoking {}".format(runtimeconfig['revoke']))
        cert_revoke(tools.read_pem_file(runtimeconfig['revoke']),
                    domainconfigs,
                    runtimeconfig['fallback_authority'],
                    runtimeconfig['revoke_reason'])
    else:
        # Mode: issue certificates (implicit)
        # post-update actions (run only once)
        actions = set()
        superseded = set()
        exceptions = list()
        # check certificate validity and obtain/renew certificates if needed
        for config in domainconfigs:

            domain = config['domainlist'][0]

            Certificate.objects.update_or_create(
                domain=domain,
                name='auto-renew_%s.pem' % domain,
                defaults={
                    'status': 1,
                }
            )

            try:
                cert = None
                if os.path.isfile(config['cert_file']):
                    cert = tools.read_pem_file(config['cert_file'])
                validate_ocsp = str(config.get('validate_ocsp')).lower() != 'false'
                if validate_ocsp and cert and os.path.isfile(config['ca_file']):
                    try:
                        issuer = tools.read_pem_file(config['ca_file'])
                    except Exception as e1:
                        log("Failed to retrieve issuer from ca file: {}. Trying to download...".format(e1))
                        try:
                            issuer = tools.download_issuer_ca(cert)
                        except Exception as e2:
                            log("Failed to download issuer for cert file: {}. Cannot validate OCSP.".format(e2))
                            validate_ocsp = False
                if not cert or ('force_renew' in runtimeconfig and all(
                        d in config['domainlist'] for d in runtimeconfig['force_renew'])) \
                        or not tools.is_cert_valid(cert, config['ttl_days']) \
                        or (validate_ocsp and not tools.is_ocsp_valid(cert, issuer, config['validate_ocsp'])):
                    cert = cert_get(config)
                    if str(config.get('cert_revoke_superseded')).lower() == 'true' and cert:
                        superseded.add(cert)

                try:
                    expiration_date = make_aware(tools.get_cert_valid_until(cert))
                except:
                    expiration_date = None

                Certificate.objects.update_or_create(
                    domain=domain,
                    name='auto-renew_%s.pem' % domain,
                    defaults={
                        'status': 0,
                        'reason': '',
                        'expiration_date': expiration_date
                    }
                )

            except Exception as e:
                Certificate.objects.update_or_create(
                    domain=domain,
                    name='auto-renew_%s.pem' % domain,
                    defaults={
                        'status': 2,
                        'reason': str(e)
                    }
                )
                log("Certificate issue/renew failed", e, error=True)
                exceptions.append(e)

        # deploy new certificates after all are renewed
        deployment_success = True
        for config in domainconfigs:
            for cfg in config['actions']:
                try:
                    if not tools.target_is_current(cfg['path'], config['cert_file']):
                        actions.add(cert_put(cfg))
                        log("Updated '{}' due to newer version".format(cfg['path']))
                except Exception as e:
                    log("Certificate deployment to {} failed".format(cfg['path']), e, error=True)
                    exceptions.append(e)
                    deployment_success = False

        # run post-update actions
        for action in actions:
            if action is not None:
                try:
                    # Run actions in a shell environment (to allow shell syntax) as stated in the configuration
                    output = subprocess.check_output(action, shell=True, stderr=subprocess.STDOUT)
                    logmsg = "Action succeeded: {}".format(action)
                    if len(output) > 0:
                        if getattr(output, 'decode', None):
                            # Decode function available? Use it to get a proper str
                            output = output.decode('utf-8')
                        logmsg += os.linesep + tools.indent(output, 18)  # 18 = len("Action succeeded: ")
                    log(logmsg)
                except subprocess.CalledProcessError as e:
                    output = e.output
                    logmsg = "Action failed: ({}) {}".format(e.returncode, e.cmd)
                    if len(output) > 0:
                        if getattr(output, 'decode', None):
                            # Decode function available? Use it to get a proper str
                            output = output.decode('utf-8')
                        logmsg += os.linesep + tools.indent(output, 15)  # 15 = len("Action failed: ")
                    log(logmsg, error=True)
                    exceptions.append(e)
                    deployment_success = False

        # revoke old certificates as superseded
        if deployment_success:
            for superseded_cert in superseded:
                try:
                    log("Revoking '{}' valid until {} as superseded".format(
                        tools.get_cert_cn(superseded_cert),
                        tools.get_cert_valid_until(superseded_cert)))
                    cert_revoke(superseded_cert, domainconfigs, runtimeconfig['fallback_authority'], reason=4)
                except Exception as e:
                    log("Certificate supersede revoke failed", e, error=True)
                    exceptions.append(e)

        # throw a RuntimeError with all exceptions caught while working if there were any
        return exceptions


def update_or_create_certs(domain='', api=None):
    result = {'success': True, 'errors': []}

    try:
        errors = main(force_renew=domain)
    except Exception as e:
        print(e)
        errors = [e]

    if errors:
        result['success'] = False
        result['errors'] = errors

    if result['success'] and api is not None:
        api.reload_config()

    return result


def update_cert_config():

    hosts = VirtualHost.objects.filter(srv_records=True, cert_records=True, issue_cert=True)

    if not os.path.exists(settings.CERT_CONF_DIR):
        os.mkdir(settings.CERT_CONF_DIR)

    # create domain config
    domain_config_data = {}
    for host in hosts:
        key = "%s *.%s" % (host.name, host.name)

        host_data = {
            "path": os.path.join(settings.CERTS_DIR, "auto-renew_%s.pem" % host.name),
            "format": "key,crt,ca"
            }
        if isinstance(settings.CERT_ACTION, str) and settings.CERT_ACTION.strip():
            host_data["action"] = settings.CERT_ACTION
        domain_config_data[key] = [host_data]

    domain_config = os.path.join(
        settings.CERT_CONF_DIR,
        settings.CERT_DOMAIN_FILENAME
    )
    with open(domain_config, 'w+') as file:
        json.dump(domain_config_data, file, indent=2)

    # create acertmgr config
    acert_config_data = {
        "authority_tos_agreement": "true",
        "authority": settings.CERT_AUTHORITY,
        "mode": "xabber_dns",
        "port": 5000
    }
    acert_config = os.path.join(
        settings.CERT_CONF_DIR,
        settings.CERT_CONF_FILENAME
    )
    with open(acert_config, 'w+') as file:
        json.dump(acert_config_data, file, indent=2)


def check_certificates():

    certificates_info = []

    if os.path.exists(settings.CERTS_DIR):
        # List all files in the specified folder
        files = os.listdir(settings.CERTS_DIR)
        for file in files:
            if file.lower().endswith('.pem'):

                full_path = os.path.join(settings.CERTS_DIR, file)

                with open(full_path, 'rb') as cert_file:
                    cert_data = cert_file.read()

                    try:
                        # Attempt to parse the certificate data
                        cert = x509.load_pem_x509_certificate(cert_data, default_backend())

                        # Extract certificate information
                        expiration_date = cert.not_valid_after
                        domain = cert.subject.rfc4514_string().replace('CN=', '')  # Remove 'CN=' prefix

                        if VirtualHost.objects.filter(name=domain).exists():
                            Certificate.objects.update_or_create(
                                name=file,
                                domain=domain,
                                defaults={
                                    'expiration_date': make_aware(expiration_date),
                                }
                            )

                            certificates_info += [file]
                    except ValueError as e:
                        print(f"Error parsing certificate in file '{file}': {e}")

    Certificate.objects.exclude(name__in=certificates_info).delete()


def validate_certificate(certificate_path):
    with open(certificate_path, 'rb') as certificate_file:
        certificate_data = certificate_file.read()

    try:
        # Load the certificate
        certificate = x509.load_pem_x509_certificate(certificate_data, default_backend())

        # Check if the certificate has a public key
        if certificate.public_key():
            # Check if the certificate has a certificate value
            if certificate.serial_number:
                # Load the private key from the same PEM file
                private_key = serialization.load_pem_private_key(
                    certificate_data,
                    password=None,
                    backend=default_backend()
                )
                # Check if the private key is an RSA key
                if isinstance(private_key, rsa.RSAPrivateKey):
                    return True
                else:
                    return False
            else:
                return False
        else:
            return False
    except Exception as e:
        print(e)  # Handle or log the exception as needed
        return False