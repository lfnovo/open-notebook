"""
Web research capabilities for notebooks.

The first capability is *source discovery*: given a topic, search the web and
turn the top hits into ``Source`` records of type ``link`` (upstream issue
#973). Provider-specific logic lives in the adapters here so the API layer
stays thin and can grow into the fuller research agent the issue describes.
"""
