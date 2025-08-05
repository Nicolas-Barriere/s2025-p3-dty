"""
DNS provisioning functionality for mail domains.
"""

import logging
from typing import Any, Dict, Optional

from django.conf import settings

from core.models import MailDomain
from core.services.dns.providers.scaleway import ScalewayDNSProvider

import dns.resolver

logger = logging.getLogger(__name__)


def detect_dns_provider(domain: str) -> Optional[str]:
    """
    Detect which DNS provider is being used for a domain.

    Args:
        domain: Domain name to check

    Returns:
        Provider name ('scaleway') or None if unknown
    """
    try:
        # Get nameservers for the domain
        nameservers = dns.resolver.resolve(domain, "NS")
        ns_names = [ns.target.to_text().rstrip(".") for ns in nameservers]

        # Check for Scaleway nameservers
        scaleway_ns = ["ns0.dom.scw.cloud", "ns1.dom.scw.cloud"]
        if any(ns in ns_names for ns in scaleway_ns):
            return "scaleway"

        return None

    except (
        dns.resolver.NXDOMAIN,
        dns.resolver.Timeout,
        dns.resolver.NoNameservers,
        dns.resolver.NoAnswer,
    ) as e:
        # Log unexpected errors but don't fail
        logger.warning("Unexpected error detecting DNS provider for %s: %s", domain, e)
        return None
    except Exception as e:  # pylint: disable=broad-exception-caught
        # Log unexpected errors but don't fail
        logger.warning("Unexpected error detecting DNS provider for %s: %s", domain, e)
        return None


def get_dns_provider(provider_name: str, **kwargs) -> Optional[Any]:
    """
    Get a DNS provider instance by name.

    Args:
        provider_name: Name of the provider
        **kwargs: Provider-specific configuration

    Returns:
        Provider instance or None if not supported
    """
    provider = None
    if provider_name == "scaleway":
        provider = ScalewayDNSProvider()

    if provider is None or not provider.is_configured():
        return None

    return provider


def provision_domain_dns(
    maildomain: MailDomain,
    provider_name: Optional[str] = None,
    pretend: bool = False,
    **provider_kwargs,
) -> Dict[str, Any]:
    """
    Provision DNS records for a mail domain.

    Args:
        maildomain: MailDomain instance to provision
        provider_name: DNS provider name (if None, will auto-detect or use default)
        pretend: If True, simulate operations without making actual changes
        **provider_kwargs: Provider-specific configuration

    Returns:
        Dictionary with provisioning results
    """
    domain = maildomain.name

    # Auto-detect provider if not specified
    if not provider_name:
        provider_name = detect_dns_provider(domain)
        if not provider_name:
            # Use default provider from environment if no provider detected
            provider_name = settings.DNS_DEFAULT_PROVIDER
            if not provider_name:
                return {
                    "success": False,
                    "error": f"Could not detect DNS provider for domain {domain} and no default provider configured",
                    "domain": domain,
                }

    # Get provider instance
    provider = get_dns_provider(provider_name, **provider_kwargs)
    if not provider:
        return {
            "success": False,
            "error": f"DNS provider '{provider_name}' is not supported or not configured",
            "domain": domain,
            "provider": provider_name,
        }

    # Get expected DNS records
    expected_records = maildomain.get_expected_dns_records()

    # Provision records
    try:
        changes = provider.provision_domain_records(
            domain, expected_records, pretend=pretend
        )
        results = {
            "success": True,
            "changes": changes,
            "domain": domain,
            "provider": provider_name,
            "pretend": pretend,
        }
        return results
    except Exception as e:  # pylint: disable=broad-exception-caught
        return {
            "success": False,
            "error": f"Failed to provision DNS records: {e}",
            "domain": domain,
            "provider": provider_name,
            "pretend": pretend,
        }
