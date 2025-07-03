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
import { useThreadsGenerateAnswerCreate } from "@/features/api/gen/threads/threads";
import { useMailboxContext } from "@/features/providers/mailbox"


export function AIGroupButton() {
    const editor = useBlockNoteEditor();
    const Components = useComponentsContext();
    const selectedBlocks = useSelectedBlocks(editor);
    const { t } = useTranslation();
    const { selectedThread, messages, queryStates } = useMailboxContext();

    if (!selectedThread) return null

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
                            action="answer"
                            icon={<span>📝</span>}
                            threadId={selectedThread.id} // Ajoute cette prop
                        >
                            {t('Generate answer')}
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
    action: string;
    icon?: ReactNode;
    threadId: string;
}

const AIMenuItemTransform = ({
    children,
    icon,
    threadId
}: PropsWithChildren<AIMenuItemTransform>) => {
    // threadId doit être passé en prop ou récupéré via contexte/props
    const { mutateAsync: generateAnswer, isPending } = useThreadsGenerateAnswerCreate();
    const editor = useBlockNoteEditor();

    const requestThreadAnswer = async (selectedBlocks: Block[]) => {
        if (!threadId) {
            throw new Error("No thread selected");
        }
        // Appel à l'API pour générer la réponse
        const response = await generateAnswer({ id: threadId });
        console.log(response);
        // Récupère la réponse générée (adapte selon la structure réelle)
        const answer = response.data.answer || "Aucune réponse générée";
        // Insère la réponse dans l'éditeur (remplace la sélection)
        const blocks = await editor.tryParseMarkdownToBlocks(answer);
        editor.replaceBlocks(selectedBlocks, blocks);
    };

    return (
        <AIMenuItem icon={icon} requestAI={requestThreadAnswer} isPending={isPending}>
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