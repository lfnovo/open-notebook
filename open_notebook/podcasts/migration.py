"""
Data migration for podcast profiles: maps legacy provider/model strings
to Model registry record IDs.

Runs on API startup after SQL migrations. Idempotent - skips profiles
that already have the new fields populated.
"""

from loguru import logger

from open_notebook.database.repository import repo_query


async def _find_model_record(
    provider: str, model_name: str, model_type: str
) -> str | None:
    """Find an existing Model record matching provider + name + type."""
    results = await repo_query(
        "SELECT * FROM model WHERE provider = $provider AND name = $name AND type = $type",
        {"provider": provider, "name": model_name, "type": model_type},
    )
    if results:
        return str(results[0]["id"])
    return None


async def _find_or_create_model(
    provider: str, model_name: str, model_type: str
) -> str | None:
    """Find existing Model record or auto-create one linked to provider credential."""
    # Try exact match first
    model_id = await _find_model_record(provider, model_name, model_type)
    if model_id:
        return model_id

    # Try to find a credential for this provider and auto-create the model
    from open_notebook.domain.credential import Credential

    credentials = await Credential.get_by_provider(provider)
    if not credentials:
        logger.warning(
            f"No credential found for provider '{provider}'. "
            f"Cannot auto-create model '{model_name}'. Profile needs manual migration."
        )
        return None

    # Use the first credential for the provider
    credential = credentials[0]
    from open_notebook.ai.models import Model

    model = Model(
        name=model_name,
        provider=provider,
        type=model_type,
        credential=str(credential.id),
    )
    await model.save()
    logger.info(
        f"Auto-created model '{model_name}' ({model_type}) "
        f"linked to credential '{credential.name}'"
    )
    return str(model.id)


async def migrate_podcast_profiles() -> None:
    """Migrate episode and speaker profiles from legacy strings to Model record IDs.

    Idempotent: skips profiles where new fields are already populated.
    """
    logger.info("Starting podcast profile data migration...")

    ep_migrated = 0
    ep_skipped = 0
    ep_failed = 0

    # Migrate EpisodeProfiles
    episode_profiles = await repo_query("SELECT * FROM episode_profile")
    for raw in episode_profiles:
        profile_name = raw.get("name", raw.get("id", "unknown"))
        try:
            outline_llm = raw.get("outline_llm")
            transcript_llm = raw.get("transcript_llm")

            needs_outline = not outline_llm
            needs_transcript = not transcript_llm

            if not needs_outline and not needs_transcript:
                ep_skipped += 1
                continue

            updates = {}

            if needs_outline:
                outline_provider = raw.get("outline_provider")
                outline_model = raw.get("outline_model")
                if outline_provider and outline_model:
                    model_id = await _find_or_create_model(
                        outline_provider, outline_model, "language"
                    )
                    if model_id:
                        from open_notebook.database.repository import ensure_record_id

                        updates["outline_llm"] = ensure_record_id(model_id)

            if needs_transcript:
                transcript_provider = raw.get("transcript_provider")
                transcript_model = raw.get("transcript_model")
                if transcript_provider and transcript_model:
                    model_id = await _find_or_create_model(
                        transcript_provider, transcript_model, "language"
                    )
                    if model_id:
                        from open_notebook.database.repository import ensure_record_id

                        updates["transcript_llm"] = ensure_record_id(model_id)

            if updates:
                from open_notebook.database.repository import repo_update

                await repo_update("episode_profile", str(raw["id"]), updates)
                ep_migrated += 1
                logger.info(
                    f"Migrated episode profile '{profile_name}': {list(updates.keys())}"
                )
            else:
                ep_failed += 1
                logger.warning(
                    f"Could not migrate episode profile '{profile_name}': "
                    "no matching models found"
                )

        except Exception as e:
            ep_failed += 1
            logger.error(f"Failed to migrate episode profile '{profile_name}': {e}")

    # Migrate SpeakerProfiles
    sp_migrated = 0
    sp_skipped = 0
    sp_failed = 0

    speaker_profiles = await repo_query("SELECT * FROM speaker_profile")
    for raw in speaker_profiles:
        profile_name = raw.get("name", raw.get("id", "unknown"))
        try:
            voice_model = raw.get("voice_model")

            if voice_model:
                sp_skipped += 1
                continue

            tts_provider = raw.get("tts_provider")
            tts_model = raw.get("tts_model")

            if not tts_provider or not tts_model:
                sp_failed += 1
                logger.warning(
                    f"Speaker profile '{profile_name}' has no legacy TTS config"
                )
                continue

            model_id = await _find_or_create_model(
                tts_provider, tts_model, "text_to_speech"
            )
            if model_id:
                from open_notebook.database.repository import ensure_record_id, repo_update

                await repo_update(
                    "speaker_profile",
                    str(raw["id"]),
                    {"voice_model": ensure_record_id(model_id)},
                )
                sp_migrated += 1
                logger.info(f"Migrated speaker profile '{profile_name}'")
            else:
                sp_failed += 1
                logger.warning(
                    f"Could not migrate speaker profile '{profile_name}': "
                    "no matching model found"
                )

        except Exception as e:
            sp_failed += 1
            logger.error(f"Failed to migrate speaker profile '{profile_name}': {e}")

    logger.info(
        f"Podcast profile migration complete. "
        f"Episodes: {ep_migrated} migrated, {ep_skipped} skipped, {ep_failed} failed. "
        f"Speakers: {sp_migrated} migrated, {sp_skipped} skipped, {sp_failed} failed."
    )
