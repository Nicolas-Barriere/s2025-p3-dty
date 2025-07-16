import { useThreadsGenerateAnswerCreate, useThreadsGenerateNewMessageCreate } from "@/features/api/gen/threads/threads";
import { BlockNoteEditor } from "@blocknote/core";
import { diffWords } from 'diff'; // Vous devez installer la bibliothèque 'diff' : npm install diff @types/diff
import { useState } from "react";

interface AIAnswerResponse {
    answer: string;
}

export const useAIAnswer = (threadId?: string) => {
    const { mutateAsync: generateAnswer, isPending: isAnswerPending } = useThreadsGenerateAnswerCreate();
    const { mutateAsync: generateNewMessage, isPending: isMessagePending } = useThreadsGenerateNewMessageCreate();
    const [originalContent, setOriginalContent] = useState<any[] | null>(null);
    const [formattedAnswer, setFormattedAnswer] = useState<string | null>(null);
    const [rawAnswer, setRawAnswer] = useState<string | null>(null);

    // Fonction pour restaurer le contenu original
    const revertChanges = (editor?: BlockNoteEditor<any, any, any>) => {
        if (editor && originalContent) {
            editor.removeBlocks(editor.document.map(block => block.id));
            editor.insertBlocks(originalContent, editor.document[editor.document.length - 1].id);
            editor.focus();
            setOriginalContent(null);
            setFormattedAnswer(null);
            setRawAnswer(null);

            return true;
        }
        return false;
    };

    // Fonction pour ne garder que la version finale (sans barré)
    const keepChanges = async (editor?: BlockNoteEditor<any, any, any>) => {
        if (editor && rawAnswer) {
            editor.removeBlocks(editor.document.map(block => block.id));
            const blocks = await editor.tryParseMarkdownToBlocks(rawAnswer);
            editor.insertBlocks(blocks, editor.document[editor.document.length - 1].id);
            editor.focus();
            setOriginalContent(null);
            setFormattedAnswer(null);
            setRawAnswer(null);
            return true;
        }
        return false;
    };

    const requestAIAnswer = async (draft: string, prompt: string, editor?: BlockNoteEditor<any, any, any>) => {
        if (editor) {
            const currentContent = JSON.parse(JSON.stringify(editor.document));
            setOriginalContent(currentContent);

            const currentMarkdown = await editor.blocksToMarkdownLossy(editor.document);
            const hasExistingContent = currentMarkdown && currentMarkdown.trim().length > 0;

            const response = threadId
                ? await generateAnswer({
                    id: threadId,
                    data: { draft, prompt },
                })
                : await generateNewMessage({
                    data: { draft, prompt },
                });

            const answer = threadId
                ? (response.data as AIAnswerResponse).answer || ""
                : (response.data as { message: string }).message || "";

            setRawAnswer(answer);

            if (hasExistingContent) {
                editor.removeBlocks(editor.document.map(block => block.id));
                let formattedContent = "";
                const differences = diffWords(currentMarkdown, answer);
                differences.forEach(part => {
                    if (part.added) {
                        formattedContent += `<span style="font-style: italic;">${part.value}</span>`;
                    } else if (part.removed) {
                        formattedContent += `<span style="text-decoration: line-through; color: #FF6666">${part.value}</span>`;
                    } else {
                        formattedContent += part.value;
                    }
                });
                setFormattedAnswer(formattedContent);

                try {
                    const html = `${formattedContent.split('\n').map(line =>
                        line ? `<p>${line}</p>` : ''
                    ).join('')}`;
                    // Essayer de convertir le HTML formaté en blocs BlockNote
                    const blocks = await editor.tryParseHTMLToBlocks(html);
                    // Si le document est vide après avoir supprimé tous les blocs
                    editor.insertBlocks(blocks, editor.document[editor.document.length - 1].id);
                } catch (error) {
                    console.error("Erreur lors de la conversion des différences en blocs:", error);
                    const blocks = await editor.tryParseMarkdownToBlocks(answer);
                    editor.insertBlocks(blocks, editor.document[editor.document.length - 1].id);
                }
            } else {
                const blocks = await editor.tryParseMarkdownToBlocks(answer);
                editor.insertBlocks(blocks, editor.document[editor.document.length - 1].id);
            }
            editor.focus();
            return {
                answer,
                hasChanges: hasExistingContent
            };
        }

        return { answer: "", hasChanges: false };
    };

    return {
        requestAIAnswer,
        isPending: isAnswerPending || isMessagePending,
        revertChanges,
        keepChanges,
        hasOriginalContent: !!originalContent
    };
};