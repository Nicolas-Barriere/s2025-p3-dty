import { useThreadsGenerateAnswerCreate } from "@/features/api/gen/threads/threads";
import { BlockNoteEditor } from "@blocknote/core";

export const useAIAnswer = (threadId?: string) => {
    const { mutateAsync: generateAnswer, isPending } = useThreadsGenerateAnswerCreate();

    const requestAIAnswer = async (context: string, editor?: BlockNoteEditor) => {
        const response = await generateAnswer({
            id: threadId ?? "",
            data: { context }
        });
        const answer = response.data.answer || "Aucune réponse générée";

        if (editor) {
            const blocks = await editor.tryParseMarkdownToBlocks(answer);
            const lastBlock = editor.document[editor.document.length - 1];
            // Insère à la fin du document
            const insertedBlocks = editor.insertBlocks(blocks, lastBlock?.id);
        }

        return answer;
    };

    return { requestAIAnswer, isPending };
};