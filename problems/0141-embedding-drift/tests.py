import numpy as np

BILLING = [
    "I was charged twice for my Pro plan this month",
    "Please refund the duplicate invoice for order 4471",
    "Can I switch from annual to monthly billing",
    "My card was declined when renewing the subscription",
    "Please send a VAT invoice for March",
    "Why did my invoice go up after adding two seats",
    "Cancel my subscription and refund the last charge",
    "The invoice shows the wrong company address",
]
LOGIN = [
    "Password reset email never arrived",
    "Locked out after too many login attempts",
    "Two factor code is not accepted on my phone",
    "How do I change the email on my account",
    "Login page says my password is wrong but it is not",
    "Reset link expired before I could use it",
]
SSO = [
    "SAML SSO login fails with an invalid audience error",
    "Okta SSO redirect loops back to the sign in page",
    "SCIM provisioning did not create our new users",
    "Azure AD SSO says the signing certificate has expired",
    "After enabling SSO our admins cannot log in",
    "SSO users get a 403 when opening shared dashboards",
    "How do we enforce SSO for every workspace member",
    "SCIM deprovisioning left deleted users with active seats",
]
EXPORT = [
    "CSV export of tickets times out for large workspaces",
    "The API returns 429 when we export audit logs",
    "Webhook deliveries to our endpoint stopped yesterday",
    "Export to S3 fails with access denied on the bucket",
]


def _sample(rng, pools, weights, n):
    out = []
    for _ in range(n):
        pool = pools[rng.choice(len(pools), p=weights)]
        out.append(pool[rng.integers(len(pool))])
    return out


def cases():
    rng = np.random.default_rng(141)
    ref_big = _sample(rng, [BILLING, LOGIN, EXPORT], [0.5, 0.35, 0.15], 40)
    same_big = _sample(rng, [BILLING, LOGIN, EXPORT], [0.5, 0.35, 0.15], 36)
    launch_big = _sample(rng, [BILLING, LOGIN, SSO], [0.3, 0.2, 0.5], 36)
    mix_shift = _sample(rng, [BILLING, LOGIN, EXPORT], [0.1, 0.2, 0.7], 30)
    return [
        {"name": "Example 1", "hidden": False,
         "args": {"reference": BILLING[:4] + LOGIN[:4], "current": BILLING[4:] + LOGIN[2:6],
                  "cos_threshold": 0.45, "mmd_threshold": 0.05},
         "explanation": "Both weeks are billing and login tickets, phrased differently. The centroids stay close and the kernel "
                        "similarities within and across windows are about the same: centroid distance 0.38 (under 0.45) and mmd2 = -0.034. No drift."},
        {"name": "Example 2", "hidden": False,
         "args": {"reference": BILLING[:4] + LOGIN[:4], "current": SSO,
                  "cos_threshold": 0.45, "mmd_threshold": 0.05},
         "explanation": "The SSO launch week. Every current ticket is about SAML, Okta or SCIM, words the reference never used. "
                        "The centroids point in different directions and the cross-window kernel term collapses, so both checks fire: centroid distance 1.24 (the centroids point slightly away from each other) and mmd2 = 0.084."},
        {"name": "Example 3", "hidden": False,
         "args": {"reference": ["Password reset email never arrived", "Locked out after too many login attempts"],
                  "current": ["Password reset email never arrived", "Locked out after too many login attempts"],
                  "cos_threshold": 0.45, "mmd_threshold": 0.05},
         "explanation": "Identical windows. The centroid distance is 0. The 6 pair distances among the 4 stacked rows are 0, 0 and four copies "
                        "of the same d, so sigma is d. Unbiased MMD subtracts the cross term, which includes the perfect self matches, so mmd2 "
                        "comes out as k(A, B) - 1 = exp(-1/2) - 1 = -0.393. A negative value is normal for the unbiased estimator."},
        {"name": "large windows same mix", "args": {"reference": ref_big, "current": same_big, "cos_threshold": 0.2, "mmd_threshold": 0.02}},
        {"name": "large windows SSO launch", "args": {"reference": ref_big, "current": launch_big, "cos_threshold": 0.2, "mmd_threshold": 0.02}},
        {"name": "topic mix shift", "args": {"reference": ref_big, "current": mix_shift, "cos_threshold": 0.2, "mmd_threshold": 0.02}},
        {"name": "ingestion bug sends empty bodies",
         "args": {"reference": BILLING[:5], "current": ["", "", "", ""], "cos_threshold": 0.2, "mmd_threshold": 0.05}},
        {"name": "uneven window sizes",
         "args": {"reference": BILLING + LOGIN, "current": EXPORT[:3], "cos_threshold": 0.45, "mmd_threshold": 0.05}},
        {"name": "half the week is the new topic",
         "args": {"reference": BILLING + LOGIN, "current": BILLING[:4] + SSO[:4], "cos_threshold": 0.45, "mmd_threshold": 0.05}},
        {"name": "bot replays two tickets",
         "args": {"reference": BILLING + LOGIN, "current": [BILLING[0], LOGIN[0]] * 6, "cos_threshold": 0.6, "mmd_threshold": 0.05}},
        {"name": "high thresholds never fire",
         "args": {"reference": BILLING, "current": SSO, "cos_threshold": 2.0, "mmd_threshold": 5.0}},
    ]
