"use client";
import * as locales from '@blocknote/core/locales';
import { BlockNoteView } from "@blocknote/mantine";
import "@blocknote/mantine/style.css";
import { useCreateBlockNote } from "@blocknote/react";
import { useTranslation } from "react-i18next";
import { BlockNoteEditorOptions, BlockSchema, InlineContentSchema, StyleSchema } from '@blocknote/core';
import MailHelper from '@/features/utils/mail-helper';
import MessageEditorToolbar from './toolbar';
import { Field, FieldProps } from '@openfun/cunningham-react';
import { useFormContext } from 'react-hook-form';
import { useEffect, useRef, useState } from 'react';
import AIToolbar from "./AIToolbar";
import { useAIAnswer } from "./utils/ai";
import { useMailboxContext } from "@/features/providers/mailbox"


type MessageEditorProps = FieldProps & {
    blockNoteOptions?: Partial<BlockNoteEditorOptions<BlockSchema, InlineContentSchema, StyleSchema>>
    defaultValue?: string;
}

/**
 * A component that allows the user to edit a message in a BlockNote editor.
 * !!! This component must be used within a FormProvider (from react-hook-form)
 * 
 * Two hidden inputs (`htmlBody` and `textBody`) are rendered to store
 * the HTML and text content of the message. Their values are updated
 * when the editor is blurred. Those inputs must be used in the parent form
 * to retrieve text and html content.
 */
const MessageEditor = ({ blockNoteOptions, defaultValue, ...props }: MessageEditorProps) => {
    const form = useFormContext();
    const { t, i18n } = useTranslation();
    const editorRef = useRef<HTMLDivElement>(null);
    const [selectedText, setSelectedText] = useState<string | null>(null);
    const [showAIToolbar, setShowAIToolbar] = useState(true);
    const { selectedThread } = useMailboxContext();
    const [message, setMessage] = useState<string | null>(null);
    const aiToolbarRef = useRef<{ focus: () => void }>(null);
    const [showActionButtons, setShowActionButtons] = useState(false);
    const { requestAIAnswer, isPending, revertChanges, keepChanges } = useAIAnswer(selectedThread?.id);
    const [lastInstruction, setLastInstruction] = useState(""); // Ajouter cet état



    // Fonction pour détecter la sélection
    const handleSelection = () => {
        const selection = window.getSelection();
        if (selection && selection.rangeCount > 0 && !selection.isCollapsed) {
            const range = selection.getRangeAt(0);
            const rect = range.getBoundingClientRect();
            const editorRect = editorRef.current?.getBoundingClientRect();
            const text = selection.toString();
            if (editorRect) {
                setSelectedText(text);
            }
        } else {
            setSelectedText(null);
        }
    };

    // Ajoute un listener sur la sélection
    useEffect(() => {
        const editorNode = editorRef.current;
        if (!editorNode) return;
        editorNode.addEventListener("mouseup", handleSelection);
        editorNode.addEventListener("keyup", handleSelection);
        return () => {
            editorNode.removeEventListener("mouseup", handleSelection);
            editorNode.removeEventListener("keyup", handleSelection);
        };
    }, []);

    const editor = useCreateBlockNote({
        tabBehavior: "prefer-navigate-ui",
        trailingBlock: false,
        initialContent: defaultValue ? JSON.parse(defaultValue) : undefined,
        dictionary: {
            ...locales[i18n.language as keyof typeof locales],
            placeholders: {
                ...locales[i18n.language as keyof typeof locales].placeholders,
                emptyDocument: t('message_editor.start_typing'),
                default: t('message_editor.start_typing'),
            }
        },
        ...blockNoteOptions,
    }, [i18n.resolvedLanguage]);

    const handleChange = async () => {
        form.setValue("messageEditorDraft", JSON.stringify(editor.document), { shouldDirty: true });
        const markdown = await editor.blocksToMarkdownLossy(editor.document);
        setMessage(markdown);
        const html = await MailHelper.markdownToHtml(markdown);
        form.setValue("messageEditorText", markdown);
        form.setValue("messageEditorHtml", html);
    }

    /**
     * Process the html and text content of the message when the editor is mounted.
     */
    useEffect(() => {
        handleChange();
    }, [])

    const toggleAIToolbar = () => {
        setShowAIToolbar(prev => {
            const newValue = !prev;

            // Si on active la barre, on met le focus après le rendu
            if (newValue) {
                // Utiliser setTimeout pour laisser React finir le rendu
                setTimeout(() => {
                    aiToolbarRef.current?.focus();
                }, 50);
            }

            return newValue;
        });
    };

    useEffect(() => {
        const handleKeyDown = (event: KeyboardEvent) => {
            // Command+Shift+P sur Mac ou Ctrl+Shift+P sur Windows
            if ((event.metaKey || event.ctrlKey) && event.shiftKey && event.key.toLowerCase() === 'l') {
                event.preventDefault(); // Empêche le comportement par défaut du navigateur
                toggleAIToolbar(); // Utiliser la nouvelle fonction
            }
        };

        // Ajoute l'écouteur d'événements
        window.addEventListener('keydown', handleKeyDown);

        // Nettoie l'écouteur d'événements lors du démontage
        return () => {
            window.removeEventListener('keydown', handleKeyDown);
        };
    }, []);

    const getCurrentMessage = async () => {
        const markdown = await editor.blocksToMarkdownLossy(editor.document);
        return markdown;
    };

    const handleRevert = () => {
        revertChanges(editor);
        setShowActionButtons(false);
    };

    const handleKeep = () => {
        keepChanges(editor);
        setLastInstruction("");
        setShowActionButtons(false);
    };

    const handleAIResponse = async (context: string) => {
        try {
            // Extraire et sauvegarder l'instruction à partir du contexte
            const instructionMatch = context.match(/La demande est : (.*?)(?:\n|$)/);
            const extractedInstruction = instructionMatch ? instructionMatch[1] : "";
            setLastInstruction(extractedInstruction);

            const result = await requestAIAnswer(context, editor);
            // Afficher les boutons d'action uniquement si des modifications ont été appliquées
            if (result.hasChanges) {
                setShowActionButtons(true);
            }
        } catch (error) {
            console.error("Erreur lors de la génération de la réponse IA:", error);
        }
    };

    return (
        <Field {...props}>
            <BlockNoteView
                editor={editor}
                theme="light"
                className="message-editor"
                sideMenu={false}
                slashMenu={false}
                formattingToolbar={false}
                onChange={handleChange}
            >
                {showAIToolbar && (
                    <AIToolbar
                        ref={aiToolbarRef}
                        threadId={selectedThread?.id}
                        editor={editor}
                        getCurrentMessage={getCurrentMessage}
                        onRevert={handleRevert}
                        onKeep={handleKeep}
                        showActionButtons={showActionButtons}
                        onAIResponse={handleAIResponse}
                        isPending={isPending}
                        lastInstruction={lastInstruction}
                    />
                )}
                <MessageEditorToolbar onAIClick={toggleAIToolbar}
                    active={showAIToolbar} />
            </BlockNoteView>
            <input {...form.register("messageEditorHtml")} type="hidden" />
            <input {...form.register("messageEditorText")} type="hidden" />
            <input {...form.register("messageEditorDraft")} type="hidden" />
        </Field>
    );
};

export default MessageEditor;
