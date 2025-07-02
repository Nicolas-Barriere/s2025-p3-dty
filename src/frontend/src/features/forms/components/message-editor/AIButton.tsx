import { Block } from '@blocknote/core';
import {
    ComponentProps,
    useBlockNoteEditor,
    useComponentsContext,
    useSelectedBlocks,
} from '@blocknote/react';
import {
    Loader,
    VariantType,
    useToastProvider,
} from '@openfun/cunningham-react';
import { PropsWithChildren, ReactNode, useMemo } from 'react';
import { useTranslation } from 'react-i18next';

import {
    AITransformActions,
    useDocAITransform,
    useDocAITranslate,
} from '@/features/forms/api';


export function AIGroupButton() {
    const editor = useBlockNoteEditor();
    const Components = useComponentsContext();
    const selectedBlocks = useSelectedBlocks(editor);
    const { t } = useTranslation();


    return (
        <Components.Generic.Menu.Root>
            <Components.Generic.Menu.Trigger>
                <Components.FormattingToolbar.Button
                    className="bn-button bn-menu-item --docs--ai-actions-menu-trigger"
                    data-test="ai-actions"
                    label="AI"
                    mainTooltip={t('AI Actions')}
                    icon={<span>✨</span>}
                />
            </Components.Generic.Menu.Trigger>
            <Components.Generic.Menu.Dropdown
                className="bn-menu-dropdown bn-drag-handle-menu --docs--ai-actions-menu"
                sub={true}
            >
                {(
                    <>
                        <AIMenuItemTransform
                            action="prompt"
                            icon={<span>📝</span>}
                        >
                            {t('Use as prompt')}
                        </AIMenuItemTransform>
                        <AIMenuItemTransform
                            action="rephrase"
                            icon={<span>🔄</span>}
                        >
                            {t('Rephrase')}
                        </AIMenuItemTransform>
                        <AIMenuItemTransform
                            action="summarize"
                            icon={<span>📋</span>}
                        >
                            {t('Summarize')}
                        </AIMenuItemTransform>
                        <AIMenuItemTransform
                            action="correct"
                            icon={<span>✅</span>}
                        >
                            {t('Correct')}
                        </AIMenuItemTransform>
                        <AIMenuItemTransform
                            action="beautify"
                            icon={<span>🎨</span>}
                        >
                            {t('Beautify')}
                        </AIMenuItemTransform>
                        <AIMenuItemTransform
                            action="emojify"
                            icon={<span>😊</span>}
                        >
                            {t('Emojify')}
                        </AIMenuItemTransform>
                    </>
                )}
            </Components.Generic.Menu.Dropdown>
        </Components.Generic.Menu.Root>
    );
}

/**
 * Item is derived from Mantime, some props seem lacking or incorrect.
 */
type ItemDefault = ComponentProps['Generic']['Menu']['Item'];
type ItemProps = Omit<ItemDefault, 'onClick'> & {
    rightSection?: ReactNode;
    closeMenuOnClick?: boolean;
    onClick: (e: React.MouseEvent) => void;
};

interface AIMenuItemTransform {
    action: AITransformActions;
    icon?: ReactNode;
}

const AIMenuItemTransform = ({
    action,
    children,
    icon,
}: PropsWithChildren<AIMenuItemTransform>) => {
    const { mutateAsync: requestAI, isPending } = useDocAITransform();
    const editor = useBlockNoteEditor();

    const requestAIAction = async (selectedBlocks: Block[]) => {
        const text = await editor.blocksToMarkdownLossy(selectedBlocks);

        const responseAI = await requestAI({
            text,
            action,
        });

        if (!responseAI?.answer) {
            throw new Error('No response from AI');
        }

        const markdown = await editor.tryParseMarkdownToBlocks(responseAI.answer);
        editor.replaceBlocks(selectedBlocks, markdown);
    };

    return (
        <AIMenuItem icon={icon} requestAI={requestAIAction} isPending={isPending}>
            {children}
        </AIMenuItem>
    );
};

interface AIMenuItemTranslate {
    language: string;
    docId: string;
    icon?: ReactNode;
}

const AIMenuItemTranslate = ({
    children,
    docId,
    icon,
    language,
}: PropsWithChildren<AIMenuItemTranslate>) => {
    const { mutateAsync: requestAI, isPending } = useDocAITranslate();
    const editor = useBlockNoteEditor();

    const requestAITranslate = async (selectedBlocks: Block[]) => {
        let fullHtml = '';
        for (const block of selectedBlocks) {
            if (Array.isArray(block.content) && block.content.length === 0) {
                fullHtml += '<p><br/></p>';
                continue;
            }

            fullHtml += await editor.blocksToHTMLLossy([block]);
        }

        const responseAI = await requestAI({
            text: fullHtml,
            language,
            docId,
        });

        if (!responseAI || !responseAI.answer) {
            throw new Error('No response from AI');
        }

        try {
            const blocks = await editor.tryParseHTMLToBlocks(responseAI.answer);
            editor.replaceBlocks(selectedBlocks, blocks);
        } catch {
            editor.replaceBlocks(selectedBlocks, selectedBlocks);
        }
    };

    return (
        <AIMenuItem
            icon={icon}
            requestAI={requestAITranslate}
            isPending={isPending}
        >
            {children}
        </AIMenuItem>
    );
};

interface AIMenuItemProps {
    requestAI: (blocks: Block[]) => Promise<void>;
    isPending: boolean;
    icon?: ReactNode;
}

const AIMenuItem = ({
    requestAI,
    isPending,
    children,
    icon,
}: PropsWithChildren<AIMenuItemProps>) => {
    const Components = useComponentsContext();
    const { toast } = useToastProvider();
    const { t } = useTranslation();

    const editor = useBlockNoteEditor();
    const handleAIError = useHandleAIError();

    const handleAIAction = async () => {
        const selectedBlocks = editor.getSelection()?.blocks ?? [
            editor.getTextCursorPosition().block,
        ];

        if (!selectedBlocks?.length) {
            toast(t('No text selected'), VariantType.WARNING);
            return;
        }

        try {
            await requestAI(selectedBlocks);
        } catch (error) {
            handleAIError(error);
        }
    };

    if (!Components) {
        return null;
    }

    const Item = Components.Generic.Menu.Item as React.FC<ItemProps>;

    return (
        <Item
            closeMenuOnClick={false}
            icon={icon}
            onClick={(e: React.MouseEvent) => {
                e.stopPropagation();
                void handleAIAction();
            }}
            rightSection={isPending ? <Loader size="small" /> : undefined}
        >
            {children}
        </Item>
    );
};

const useHandleAIError = () => {
    const { toast } = useToastProvider();
    const { t } = useTranslation();

    return (error: unknown) => {
        if (error.status === 429) {
            toast(t('Too many requests. Please wait 60 seconds.'), VariantType.ERROR);
            return;
        }

        toast(t('AI seems busy! Please try again.'), VariantType.ERROR);
    };
};
