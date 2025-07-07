import { useThreadsGenerateAnswerCreate } from "@/features/api/gen/threads/threads";
import { BlockNoteEditor } from "@blocknote/core";

export const useAIAnswer = (threadId?: string) => {
    const { mutateAsync: generateAnswer, isPending } = useThreadsGenerateAnswerCreate();

    const requestAIAnswer = async (context: string, editor?: BlockNoteEditor) => {
        const response = await generateAnswer({
            id: threadId ?? "",
            data: { context }
        });
        const answer = response.data.answer || "";

        if (editor) {
            const blocks = await editor.tryParseMarkdownToBlocks(answer);
            editor.removeBlocks(editor.document.map(block => block.id));
            const insertedBlocks = editor.insertBlocks(blocks, editor.document[0]);
            editor.focus();
        }

        return answer;
    };

    return { requestAIAnswer, isPending };
};