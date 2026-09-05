import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, status

from db.repository import ForgeRepository
from schemas.account import AccountCreate, AccountResponse
from schemas.onboarding import OnboardingRequest, OnboardingResponse
from schemas.website import WebsiteResponse

logger = logging.getLogger("forge.api.onboarding")

router = APIRouter(prefix="/onboarding", tags=["Onboarding"])


@router.post("/", response_model=OnboardingResponse, status_code=status.HTTP_201_CREATED)
def onboard_website_and_accounts(request: OnboardingRequest):
    """
    ONBOARDING API:
    Saves a target website and its associated user accounts to PostgreSQL in a single cohesive call.
    - Upserts the website record (url, domain, is_active, timestamps).
    - Upserts one or many associated test accounts (username, password, role, credentials JSON).
    """
    # 1. Resolve URL from either root level or nested website object
    target_url = request.url
    is_active = request.is_active
    if not target_url and request.website:
        target_url = request.website.url
        is_active = request.website.is_active

    if not target_url or not target_url.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="A valid website URL must be provided in 'url' or 'website.url'.",
        )

    target_url = target_url.strip()
    logger.info(f"[ONBOARDING API] Onboarding website: {target_url} with {len(request.accounts)} account(s)...")

    # 2. Persist website into database
    try:
        website_row = ForgeRepository.create_website(url=target_url, is_active=is_active)
    except Exception as e:
        logger.error(f"[ONBOARDING API] Failed to save website '{target_url}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to persist website to database: {str(e)}",
        )

    website_id = website_row["id"]
    logger.info(f"[ONBOARDING API] Website persisted with ID={website_id}, Domain={website_row.get('domain')}")

    # 3. Persist accounts associated with this website
    created_accounts: List[Dict[str, Any]] = []
    for acc in request.accounts:
        try:
            account_row = ForgeRepository.create_account(
                website_id=website_id,
                username=acc.username.strip(),
                password=acc.password,
                role=acc.role,
                credentials=acc.credentials or {},
                is_active=acc.is_active,
            )
            created_accounts.append(account_row)
            logger.info(f"[ONBOARDING API] Added account '{acc.username}' (role='{acc.role}') for website ID={website_id}")
        except Exception as acc_err:
            logger.error(f"[ONBOARDING API] Failed to create account '{acc.username}' for website ID={website_id}: {acc_err}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to save account '{acc.username}': {str(acc_err)}",
            )

    # Fetch updated list of all accounts for this website
    all_accounts = ForgeRepository.list_accounts_for_website(website_id=website_id)

    return OnboardingResponse(
        status="success",
        message=f"Successfully onboarded {website_row['domain']} (ID: {website_id}) with {len(all_accounts)} account(s).",
        website=WebsiteResponse.model_validate(website_row),
        accounts=[AccountResponse.model_validate(a) for a in all_accounts],
    )


@router.get("/{website_id}", response_model=Dict[str, Any])
def get_onboarding_details(website_id: int):
    """Retrieves full onboarding details for a website, including its registered accounts."""
    website = ForgeRepository.get_website_by_id(website_id)
    if not website:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Website ID {website_id} not found.")

    accounts = ForgeRepository.list_accounts_for_website(website_id)
    return {
        "website": WebsiteResponse.model_validate(website),
        "accounts": [AccountResponse.model_validate(a) for a in accounts],
        "account_count": len(accounts),
    }


@router.post("/{website_id}/accounts", response_model=AccountResponse, status_code=status.HTTP_201_CREATED)
def add_account_to_website(website_id: int, account: AccountCreate):
    """Adds a new user or admin account to an existing onboarded website."""
    website = ForgeRepository.get_website_by_id(website_id)
    if not website:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Website ID {website_id} not found.")

    try:
        account_row = ForgeRepository.create_account(
            website_id=website_id,
            username=account.username.strip(),
            password=account.password,
            role=account.role,
            credentials=account.credentials or {},
            is_active=account.is_active,
        )
        return AccountResponse.model_validate(account_row)
    except Exception as e:
        logger.error(f"[ONBOARDING API] Error adding account to website {website_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add account: {str(e)}",
        )


@router.get("/{website_id}/accounts", response_model=List[AccountResponse])
def list_website_accounts(website_id: int, role: Optional[str] = None, active_only: bool = False):
    """Lists all accounts belonging to a website, optionally filtered by role or active status."""
    website = ForgeRepository.get_website_by_id(website_id)
    if not website:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Website ID {website_id} not found.")

    accounts = ForgeRepository.list_accounts_for_website(
        website_id=website_id,
        role=role,
        active_only=active_only,
    )
    return [AccountResponse.model_validate(a) for a in accounts]
