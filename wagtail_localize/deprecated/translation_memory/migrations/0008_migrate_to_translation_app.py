# Generated by Django 2.2.9 on 2020-01-08 15:32

import uuid
import re
from django.db import migrations


DOT_DIGIT_RE = re.compile(r"\.\d{,2}$")


def get_path_id(path):
    return uuid.uuid5(uuid.UUID("fcab004a-2b50-11ea-978f-2e728ce88125"), path)


def migrate_to_translation_app(apps, schema_editor):
    Segment = apps.get_model("wagtail_localize_translation_memory.Segment")
    SegmentTranslation = apps.get_model(
        "wagtail_localize_translation_memory.SegmentTranslation"
    )
    SegmentPageLocation = apps.get_model(
        "wagtail_localize_translation_memory.SegmentPageLocation"
    )

    NewTranslatableObject = apps.get_model(
        "wagtail_localize_translation.TranslatableObject"
    )
    NewSegment = apps.get_model("wagtail_localize_translation.Segment")
    NewSegmentTranslationContext = apps.get_model(
        "wagtail_localize_translation.SegmentTranslationContext"
    )
    NewSegmentTranslation = apps.get_model(
        "wagtail_localize_translation.SegmentTranslation"
    )

    ContentType = apps.get_model("contenttypes.ContentType")

    # Copy segments
    segment_id_mapping = {}
    for segment in Segment.objects.iterator():
        new_segment, created = NewSegment.objects.get_or_create(
            language_id=segment.language_id,
            text_id=segment.text_id,
            defaults={"text": segment.text,},
        )

        segment_id_mapping[segment.id] = new_segment.id

    # Copy translations
    for segment_page_location in SegmentPageLocation.objects.select_related(
        "page_revision", "page_revision__page", "page_revision__page__content_type"
    ).iterator():
        new_segment_id = segment_id_mapping[segment_page_location.segment_id]

        # Get specific page
        page = segment_page_location.page_revision.page
        page_model = apps.get_model(
            page.content_type.app_label, page.content_type.model
        )
        page_translation_model = page_model._meta.get_field("locale").model
        page_specific = page_model.objects.get(id=page.id)
        language_id = page_specific.locale.language_id

        # Create translatable object
        object, object_created = NewTranslatableObject.objects.get_or_create(
            translation_key=page_specific.translation_key,
            content_type=ContentType.objects.get_for_model(page_translation_model),
        )

        # Remove .number from end of contexts
        # These were only used by rich text fields to note which paragraph
        # was being translated. They were removed in order to make contexts stable.
        content_path = DOT_DIGIT_RE.sub("", segment_page_location.path)

        # Create context
        (
            context,
            context_created,
        ) = NewSegmentTranslationContext.objects.get_or_create(
            object=object,
            path_id=get_path_id(content_path),
            defaults={"path": content_path},
        )

        # Copy translations
        for translation in SegmentTranslation.objects.filter(
            translation_of_id=segment_page_location.segment_id
        ).iterator():
            NewSegmentTranslation.objects.get_or_create(
                translation_of_id=new_segment_id,
                language_id=translation.language_id,
                context=context,
                defaults={
                    "text": translation.text,
                    "created_at": translation.created_at,
                    "updated_at": translation.updated_at,
                },
            )


class Migration(migrations.Migration):

    dependencies = [
        ("wagtail_localize_translation_memory", "0007_non_conflicting_related_names"),
        ("wagtail_localize_translation", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(migrate_to_translation_app, migrations.RunPython.noop),
    ]
