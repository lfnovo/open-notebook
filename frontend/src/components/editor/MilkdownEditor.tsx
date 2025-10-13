import { useEffect, useRef } from 'react';
import { Milkdown, MilkdownProvider, useEditor } from '@milkdown/react';
import { Crepe } from '@milkdown/crepe';
import { replaceAll } from '@milkdown/utils';

import "@milkdown/crepe/theme/common/style.css";
import "@milkdown/crepe/theme/frame.css";

import { cn } from '@/lib/utils';

interface MilkdownEditorProps {
  value: string;
  onChange?: (markdown: string) => void;
  className?: string;
  editable?: boolean;
}

type MilkdownEditorCoreProps = Omit<MilkdownEditorProps, 'className'>;

const CrepeEditor = ({ value, onChange, editable = true }: MilkdownEditorCoreProps) => {
  const latestValueRef = useRef(value);
  const onChangeRef = useRef(onChange);
  const crepeRef = useRef<Crepe | null>(null);

  useEffect(() => {
    onChangeRef.current = onChange;
  }, [onChange]);

  const { get, loading } = useEditor(
    (root) => {
      const crepe = new Crepe({ root, defaultValue: latestValueRef.current });
      crepeRef.current = crepe;

      if (!editable) {
        crepe.setReadonly(true);
      }

      crepe.on((listener) => {
        listener.markdownUpdated((_, markdown) => {
          if (markdown === latestValueRef.current) return;
          latestValueRef.current = markdown;
          onChangeRef.current?.(markdown);
        });
      });

      return crepe;
    },
    []
  );

  useEffect(() => {
    if (loading) return;
    const editor = get();
    if (!editor) return;
    if (value === latestValueRef.current) return;

    latestValueRef.current = value;
    editor.action(replaceAll(value));
  }, [value, get, loading]);

  useEffect(() => {
    if (loading) return;
    const crepe = crepeRef.current;
    if (!crepe) return;

    crepe.setReadonly(!editable);
  }, [editable, loading]);

  return <Milkdown />;
};

const MilkdownEditor = ({ className, ...props }: MilkdownEditorProps) => {
  return (
    <MilkdownProvider>
      <div className={cn('milkdown-container flex-1 min-h-0 min-w-0 h-full w-full overflow-y-auto', className)}>
        <CrepeEditor {...props} />
      </div>
    </MilkdownProvider>
  );
};

export default MilkdownEditor;
