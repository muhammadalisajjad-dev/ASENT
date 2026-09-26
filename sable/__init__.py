"""SABLE: local, evidence-producing least-privilege regression analysis for
Terraform S3/IAM configurations.

Pipeline stages:

    obligation  (sable.obligation)   declared boundary + baseline validation
    correspondence (sable.correspondence) successor attribution from bounded evidence
    authorize   (sable.authorize)    independent obligation verification
    verify      (sable.verify)       decision: PRESERVED | REGRESSED | UNKNOWN
"""

__all__ = ["authorize", "correspondence", "obligation", "policy", "verify"]
