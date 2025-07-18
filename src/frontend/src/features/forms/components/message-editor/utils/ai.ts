import { useThreadsGenerateAnswerCreate, useThreadsGenerateNewMessageCreate } from "@/features/api/gen/threads/threads";
import { BlockNoteEditor } from "@blocknote/core";
import { diffWords } from 'diff'; // Vous devez installer la bibliothèque 'diff' : npm install diff @types/diff
import { Span } from "next/dist/trace";
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

    function addTagToNewlines(text: string, tag: string): string {
        if (!text.trim()) return text;
        let ends_with_return = false;
        if (text[text.length - 1] === "\n") {
            ends_with_return = true;
            text = text.slice(0, -1);
            if (text[text.length - 1] === "\n") {
                text = text.slice(0, -1);
            }
        }
        let newText = `(${tag})`;
        for (let i = 0; i < text.length; i++) {
            if (text[i] === "\n" && i != 0) {
                newText += `(/${tag})\n(${tag})`;
            } else {
                newText += text[i];
                if (i === text.length - 1) {
                    newText += `(/${tag})`;
                }
            }
        }
        if (ends_with_return) {
            newText += "\n";
        }
        return newText;
    }

    function extractRemovedAndUnchanged(text: string): string {
        let newText = text;
        let cleaned = newText.replace(/\(ADDEDGREEN\)(.*?)\(\/ADDEDGREEN\)/g, "");
        cleaned = cleaned.replace(/\(REMOVEDRED\)/g, "").replace(/\(\/REMOVEDRED\)/g, "");
        return cleaned;
    }

    function extractAddedAndUnchanged(text: string): string {
        let newText = text;
        let cleaned = newText.replace(/\(REMOVEDRED\)(.*?)\(\/REMOVEDRED\)/g, "");
        cleaned = cleaned.replace(/\(ADDEDGREEN\)/g, "").replace(/\(\/ADDEDGREEN\)/g, "");
        return cleaned;
    }

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
            console.log(answer);
            if (hasExistingContent) {
                editor.removeBlocks(editor.document.map(block => block.id));
                let formattedContent = "";
                const differences = diffWords(currentMarkdown, answer);
                differences.forEach(part => {
                    if (part.added) {
                        formattedContent += addTagToNewlines(part.value, "ADDEDGREEN");
                    } else if (part.removed) {
                        formattedContent += addTagToNewlines(part.value, "REMOVEDRED");
                    } else {
                        formattedContent += part.value;
                    }
                });
                setFormattedAnswer(formattedContent);
                try {
                    const html = `${formattedContent.split('\n').map(line =>
                        line ? `<p>${line}</p>` : ''
                    ).join('')}`;
                    let blocks = await editor.tryParseHTMLToBlocks(html);
                    for (let i = 0; i < blocks.length; i++) {
                        const block = blocks[i];
                        const text = block.content ? (block.content as any)[0].text.toString() : "";
                        if (text.includes("ADDEDGREEN")) {
                            if (text.includes("REMOVEDRED")) {
                                let duplicatedBlock = JSON.parse(JSON.stringify(block));
                                block.props.backgroundColor = "red";
                                (block.content as any)[0].text = extractRemovedAndUnchanged(text);
                                duplicatedBlock.props.backgroundColor = "green";
                                (duplicatedBlock.content as any)[0].text = extractAddedAndUnchanged(text);
                                blocks.splice(i + 1, 0, duplicatedBlock);
                                i++;
                            } else {
                                block.props.backgroundColor = "green";
                                (block.content as any)[0].text = extractAddedAndUnchanged(text);
                            }
                        } else {
                            if (text.includes("REMOVEDRED")) {
                                block.props.backgroundColor = "red";
                                (block.content as any)[0].text = extractRemovedAndUnchanged(text);
                            }
                        }
                    };
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