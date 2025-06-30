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
import { useEffect } from 'react';

/**
 * Converts various content formats to BlockNote blocks array
 */
const convertToBlockNoteFormat = (content: string): any[] | undefined => {
    if (!content) return undefined;
    
    try {
        const parsed = JSON.parse(content);
        
        // Check if it's already a BlockNote blocks array
        if (Array.isArray(parsed)) {
            return parsed;
        }
        
        // Handle the draft_body format from backend: { content: "text", format: "text" }
        if (parsed && typeof parsed === 'object' && parsed.content) {
            return [
                {
                    id: "initial-block",
                    type: "paragraph",
                    props: {},
                    content: [
                        {
                            type: "text",
                            text: parsed.content,
                            styles: {}
                        }
                    ],
                    children: []
                }
            ];
        }
        
        // If it's some other format, return undefined to use empty editor
        return undefined;
    } catch (error) {
        console.warn('Failed to parse content for MessageEditor:', error);
        return undefined;
    }
};

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
    
    const editor = useCreateBlockNote({
        tabBehavior: "prefer-navigate-ui",
        trailingBlock: false,
        initialContent: convertToBlockNoteFormat(defaultValue || ""),
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
                <MessageEditorToolbar />
            </BlockNoteView>
            <input {...form.register("messageEditorHtml")} type="hidden" />
            <input {...form.register("messageEditorText")} type="hidden" />
            <input {...form.register("messageEditorDraft")} type="hidden" />
        </Field>
    );
};

export default MessageEditor;
