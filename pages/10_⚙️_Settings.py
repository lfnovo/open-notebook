import os

import streamlit as st

from api.settings_service import settings_service
from pages.stream_app.utils import setup_page

setup_page("⚙️ Settings")

st.header("⚙️ Settings")

content_settings = settings_service.get_settings()

with st.container(border=True):
    st.markdown("**Content Processing Engine for Documents**")

    default_content_processing_engine_doc = st.selectbox(
        "Default Content Processing Engine for Documents",
        ["auto", "docling", "simple"],
        index=(
            ["auto", "docling", "simple"].index(
                content_settings.default_content_processing_engine_doc
            )
            if content_settings.default_content_processing_engine_doc
            else 0
        ),
    )
    with st.expander("Help me choose"):
        st.markdown(
            "- Docling is a little slower but more accurate, specially if the documents contain tables and images.\n- Simple will extract any content from the document without formatiing it. It's ok for simple documents, but will lose quality in complex ones.\n- Auto (recommended) will try to process through docling and default to simple."
        )


with st.container(border=True):
    st.markdown("**Content Processing Engine for URLs**")
    firecrawl_enabled = os.getenv("FIRECRAWL_API_KEY") is not None
    jina_enabled = os.getenv("JINA_API_KEY") is not None

    default_content_processing_engine_url = st.selectbox(
        "Default Content Processing Engine for URLs",
        ["auto", "firecrawl", "jina", "simple"],
        index=(
            ["auto", "firecrawl", "jina", "simple"].index(
                content_settings.default_content_processing_engine_url
            )
            if content_settings.default_content_processing_engine_url
            else 0
        ),
    )
    if not firecrawl_enabled and default_content_processing_engine_url in [
        "firecrawl",
        "auto",
    ]:
        st.warning(
            "Firecrawl API Key missing. You need to add FIRECRAWL_API_KEY to use it. Get a key at [Firecrawl](https://firecrawl.dev/). If you don't add one, it will default to Jina."
        )
    if not jina_enabled and default_content_processing_engine_url in [
        "jina",
        "auto",
    ]:
        st.warning(
            "Jina API Key missing. It will work for a few requests a day, but fallback to simple afterwards. Please add JINA_API_KEY to prevent that. Get a key at [Jina.ai](https://jina.ai/)."
        )
    with st.expander("Help me choose"):
        st.markdown(
            "- Firecrawl is a paid service (with a free tier), and very powerful.\n- Jina is a good option as well and also has a free tier.\n- Simple will use basic HTTP extraction and will miss content on javascript-based websites.\n- Auto (recommended) will try to use firecrawl (if API Key is present). Then, it will use Jina until reaches the limit (or will keep using Jina if you setup the API Key). It will fallback to simple, when none of the previous options is possible."
        )

with st.container(border=True):
    st.markdown("**Content Embedding for Vector Search**")

    default_embedding_option = st.selectbox(
        "Default Embedding Option for Vector Search",
        ["ask", "always", "never"],
        index=(
            ["ask", "always", "never"].index(content_settings.default_embedding_option)
            if content_settings.default_embedding_option
            else 0
        ),
    )

    with st.expander("Help me choose"):
        st.markdown(
            "Embedding the content will make it easier to find by you and by your AI agents. If you are running a local embedding model (Ollama, for example), you shouldn't worry about cost and just embed everything. For online providers, you migtht want to be careful only if you process a lot of content (like 100s of documents at a day)."
        )
        st.markdown(
            "\n\n- Choose **always** if you are running a local embedding model or if your content volume is not that big\n- Choose **ask** if you want to decide every time\n- Choose **never** if you don't care about vector search or do not have an embedding provider."
        )
        st.markdown(
            "As a reference, OpenAI's text-embedding-3-small costs about 0.02 for 1 million tokens -- which is about 30 times the [Wikipedia page for Earth](https://en.wikipedia.org/wiki/Earth). With Gemini API, Text Embedding 004 is free with a rate limit of 1500 requests per minute."
        )

with st.container(border=True):
    st.markdown("**Auto Delete Uploaded Files**")
    auto_delete_files = st.selectbox(
        "Auto Delete Uploaded Files",
        ["yes", "no"],
        index=(
            ["yes", "no"].index(content_settings.auto_delete_files)
            if content_settings.auto_delete_files
            else 0
        ),
    )
    with st.expander("Help me choose"):
        st.markdown(
            "Once your files are uploaded and processed, they are not required anymore. Most users should allow Open Notebook to delete uploaded files from the upload folder automatically. Choose **no**, ONLY if you are using Notebook as the primary storage location for those files (which you shouldn't be at all). This option will soon be deprecated in favor of always downloading the files."
        )
        st.markdown(
            "\n\n- Choose **yes** if you are running a local embedding model or if your content volume is not that big\n- Choose **ask** if you want to decide every time\n- Choose **never** if you don't care about vector search or do not have an embedding provider."
        )

with st.container(border=True):
    st.markdown("**YouTube Preferred Languages**")
    st.caption(
        "Languages to prioritize when downloading YouTube transcripts (in order of preference). If the video does not include these languages, we'll get the best transcript possible. Don't worry, the language model will still be able to understand it. "
    )

    # Available language options with descriptions
    language_options = {
        "af": "Afrikaans",
        "ak": "Akan",
        "sq": "Albanian",
        "am": "Amharic",
        "ar": "Arabic",
        "hy": "Armenian",
        "as": "Assamese",
        "ay": "Aymara",
        "az": "Azerbaijani",
        "bn": "Bangla",
        "eu": "Basque",
        "be": "Belarusian",
        "bho": "Bhojpuri",
        "bs": "Bosnian",
        "bg": "Bulgarian",
        "my": "Burmese",
        "ca": "Catalan",
        "ceb": "Cebuano",
        "zh": "Chinese",
        "zh-HK": "Chinese (Hong Kong)",
        "zh-CN": "Chinese (China)",
        "zh-SG": "Chinese (Singapore)",
        "zh-TW": "Chinese (Taiwan)",
        "zh-Hans": "Chinese (Simplified)",
        "zh-Hant": "Chinese (Traditional)",
        "hak-TW": "Hakka Chinese (Taiwan)",
        "nan-TW": "Min Nan Chinese (Taiwan)",
        "co": "Corsican",
        "hr": "Croatian",
        "cs": "Czech",
        "da": "Danish",
        "dv": "Divehi",
        "nl": "Dutch",
        "en": "English",
        "en-US": "English (United States)",
        "eo": "Esperanto",
        "et": "Estonian",
        "ee": "Ewe",
        "fil": "Filipino",
        "fi": "Finnish",
        "fr": "French",
        "gl": "Galician",
        "lg": "Ganda",
        "ka": "Georgian",
        "de": "German",
        "el": "Greek",
        "gn": "Guarani",
        "gu": "Gujarati",
        "ht": "Haitian Creole",
        "ha": "Hausa",
        "haw": "Hawaiian",
        "iw": "Hebrew",
        "hi": "Hindi",
        "hmn": "Hmong",
        "hu": "Hungarian",
        "is": "Icelandic",
        "ig": "Igbo",
        "id": "Indonesian",
        "ga": "Irish",
        "it": "Italian",
        "ja": "Japanese",
        "jv": "Javanese",
        "kn": "Kannada",
        "kk": "Kazakh",
        "km": "Khmer",
        "rw": "Kinyarwanda",
        "ko": "Korean",
        "kri": "Krio",
        "ku": "Kurdish",
        "ky": "Kyrgyz",
        "lo": "Lao",
        "la": "Latin",
        "lv": "Latvian",
        "ln": "Lingala",
        "lt": "Lithuanian",
        "lb": "Luxembourgish",
        "mk": "Macedonian",
        "mg": "Malagasy",
        "ms": "Malay",
        "ml": "Malayalam",
        "mt": "Maltese",
        "mi": "Māori",
        "mr": "Marathi",
        "mn": "Mongolian",
        "ne": "Nepali",
        "nso": "Northern Sotho",
        "no": "Norwegian",
        "ny": "Nyanja",
        "or": "Odia",
        "om": "Oromo",
        "ps": "Pashto",
        "fa": "Persian",
        "pl": "Polish",
        "pt": "Portuguese",
        "pa": "Punjabi",
        "qu": "Quechua",
        "ro": "Romanian",
        "ru": "Russian",
        "sm": "Samoan",
        "sa": "Sanskrit",
        "gd": "Scottish Gaelic",
        "sr": "Serbian",
        "sn": "Shona",
        "sd": "Sindhi",
        "si": "Sinhala",
        "sk": "Slovak",
        "sl": "Slovenian",
        "so": "Somali",
        "st": "Southern Sotho",
        "es": "Spanish",
        "su": "Sundanese",
        "sw": "Swahili",
        "sv": "Swedish",
        "tg": "Tajik",
        "ta": "Tamil",
        "tt": "Tatar",
        "te": "Telugu",
        "th": "Thai",
        "ti": "Tigrinya",
        "ts": "Tsonga",
        "tr": "Turkish",
        "tk": "Turkmen",
        "uk": "Ukrainian",
        "ur": "Urdu",
        "ug": "Uyghur",
        "uz": "Uzbek",
        "vi": "Vietnamese",
        "cy": "Welsh",
        "fy": "Western Frisian",
        "xh": "Xhosa",
        "yi": "Yiddish",
        "yo": "Yoruba",
        "zu": "Zulu",
        "en-GB": "English (UK)",
    }

    # Get current preferred languages or use defaults
    current_languages = content_settings.youtube_preferred_languages or [
        "en",
        "pt",
        "es",
        "de",
        "nl",
        "en-GB",
        "fr",
        "de",
        "hi",
        "ja",
    ]

    youtube_preferred_languages = st.multiselect(
        "Select preferred languages (in order of preference)",
        options=list(language_options.keys()),
        default=current_languages,
        format_func=lambda x: f"{language_options[x]} ({x})",
        help="YouTube transcripts will be downloaded in the first available language from this list",
    )

    with st.expander("Help me choose"):
        st.markdown(
            "When processing YouTube videos, Open Notebook will try to download transcripts in your preferred languages. "
            "The order matters - it will try the first language first, then the second if the first isn't available, and so on. "
            "If none of your preferred languages are available, it will fall back to any available transcript."
        )
        st.markdown(
            "**Tip**: Put your most preferred language first. For example, if you speak both English and Spanish, "
            "but prefer English content, put 'en' before 'es' in your selection."
        )

if st.button("Save", key="save_settings"):
    content_settings.default_content_processing_engine_doc = (
        default_content_processing_engine_doc
    )
    content_settings.default_content_processing_engine_url = (
        default_content_processing_engine_url
    )
    content_settings.default_embedding_option = default_embedding_option
    content_settings.auto_delete_files = auto_delete_files
    content_settings.youtube_preferred_languages = youtube_preferred_languages
    settings_service.update_settings(content_settings)
    st.toast("Settings saved successfully!")
