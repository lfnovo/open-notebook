# Transformations

Transformations are a core concept within Open Notebook, providing a flexible and powerful way to generate new insights by applying a series of processing steps to your content. Inspired on the [Fabric framework](https://github.com/danielmiessler/fabric), Transformations allow you to customize how information is distilled, summarized, and enriched, opening up new ways to understand and engage with your research.

## What is a Transformation?

A **Transformation** modifies text input to produce a different output. Whether you're summarizing an article, generating key insights, or creating reflective questions, Transformations allow you to automate and enrich the processing of your content.

## Creating a Transformation

You can edit the default transformations or create your own in the Transformations UI.
![New Notebook](/assets/new_transformation.png)

When setting up the transformation, you need to configure: 

- Name (just for your reference)
- Title (will be the title of all cards created by the transformation)
- Description (will be shown as a hint in the UI)
- Prompt (the actual prompt that will be applied)
- Apply Default (will suggest this transformation for all new sources)

### Default Transformation Prompt

In this page, you can also change the Default Transformation Prompt which is a text that will be prepended to all transformations. This is useful to set up common instructions that you want to apply to all transformations, such as tone, style, or specific requirements. The default value also has some instructions to prevent the model from refusing to act due to copyright.


## Using Transformations

Your custom Patterns automatically appear on the Sources page in Open Notebook. Select and apply them to your content as you research and explore. Note patterns will be added soon, enabling transformation of both sources and personal notes.


## Experimenting different transformations and models

In the Playground page, you'll be able to choose from your installed models and defined transformations and see how they compare. Use this feature to test your transformation prompts to achieve your desired effect.

## Sky's the Limit

Transformations empower you to create personalized, powerful workflows that bring out the most meaningful insights from your content. Whether you're working with articles, papers, notes, or other media, you can craft specific and meaningful outcomes tailored to your research goals.

<style scoped>
.custom-block.tip {
  border-color: var(--vp-c-brand);
  background-color: var(--vp-c-brand-dimm);
}

.custom-block.tip .custom-block-title {
  color: var(--vp-c-brand-darker);
}
</style>