import { useEffect, useRef } from 'react';
import { Milkdown, MilkdownProvider, useEditor } from '@milkdown/react';
import type { Ctx } from '@milkdown/ctx';
import { Editor, defaultValueCtx, editorViewOptionsCtx, rootCtx } from '@milkdown/core';
import { nord } from '@milkdown/theme-nord';
import { commonmark } from '@milkdown/preset-commonmark';
import { gfm } from '@milkdown/preset-gfm';
import { listener, listenerCtx } from '@milkdown/plugin-listener';
import { replaceAll } from '@milkdown/utils';

import { cn } from '@/lib/utils';

const nordPlugin = (ctx: Ctx) => {
  nord(ctx);
  return () => undefined;
};

interface MilkdownEditorProps {
  value: string;
  onChange?: (markdown: string) => void;
  className?: string;
  editable?: boolean;
}

const EditorInstance = ({ value, onChange, editable = true }: MilkdownEditorProps) => {
  const latestValue = useRef(value);
  const latestEditable = useRef(editable);
  latestValue.current = value;
  latestEditable.current = editable;

  const { get } = useEditor(
    (root) =>
      Editor.make()
        .config((ctx) => {
          ctx.set(rootCtx, root);
          ctx.set(defaultValueCtx, value);
          ctx.get(listenerCtx).markdownUpdated((_, markdown) => {
            if (markdown !== latestValue.current) {
              latestValue.current = markdown;
              onChange?.(markdown);
            }
          });
        })
        .use(nordPlugin)
        .use(commonmark)
        .use(gfm)
        .use(listener),
    [onChange],
  );

  useEffect(() => {
    const editor = get();
    if (!editor) return;
    if (value === latestValue.current) return;
    latestValue.current = value;
    editor.action(replaceAll(value));
  }, [value, get]);

  useEffect(() => {
    const editor = get();
    if (!editor) return;
    if (editable === latestEditable.current) return;
    latestEditable.current = editable;
    editor.action((ctx) => {
      ctx.update(editorViewOptionsCtx, (prev) => ({
        ...prev,
        editable: () => editable,
      }));
    });
  }, [editable, get]);

  return <Milkdown />;
};

const MilkdownEditor = ({ className, ...props }: MilkdownEditorProps) => {
  return (
    <MilkdownProvider>
      <div className={cn('milkdown-container', className)}>
        <EditorInstance {...props} />
      </div>
    </MilkdownProvider>
  );
};

export default MilkdownEditor;
