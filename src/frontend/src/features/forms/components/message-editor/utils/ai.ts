import { useThreadsGenerateAnswerCreate } from "@/features/api/gen/threads/threads";
import { BlockNoteEditor } from "@blocknote/core";
import { diffWords } from 'diff'; // Vous devez installer la bibliothèque 'diff' : npm install diff @types/diff

interface AIAnswerResponse {
    answer: string;
}

export const useAIAnswer = (threadId?: string) => {
    const { mutateAsync: generateAnswer, isPending } = useThreadsGenerateAnswerCreate();

    const requestAIAnswer = async (context: string, editor?: BlockNoteEditor) => {

        const currentMarkdown = editor ?
            await editor.blocksToMarkdownLossy(editor.document) : "";
        const hasExistingContent = currentMarkdown && currentMarkdown.trim().length > 0;


        const response = await generateAnswer({
            id: threadId ?? "",
            data: { context }
        });
        const responseData = response.data as AIAnswerResponse;
        const answer = responseData.answer || "";

        if (editor) {
            if (hasExistingContent) {
                // Supprimer tous les blocs existants pour repartir de zéro
                editor.removeBlocks(editor.document.map(block => block.id));

                // Construire un nouveau markdown avec des balises de formatage pour les différences
                let formattedContent = "";

                // Séparer le texte en paragraphes pour préserver la structure
                const currentParagraphs = currentMarkdown.split('\n\n');
                const answerParagraphs = answer.split('\n\n');

                // Obtenir les différences mot par mot pour tout le texte
                const differences = diffWords(currentMarkdown, answer);

                // Convertir les différences en markdown formaté
                differences.forEach(part => {
                    if (part.added) {
                        // Texte ajouté - mettre en italique
                        formattedContent += `<span style="font-style: italic;">${part.value}</span>`;
                    } else if (part.removed) {
                        // Texte supprimé - barré
                        formattedContent += `<span style="text-decoration: line-through; color: #FF6666">${part.value}</span>`;
                    } else {
                        // Texte inchangé
                        formattedContent += part.value;
                    }
                });
                console.log(formattedContent);

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

                    // Fallback : utiliser simplement les blocs de la réponse de l'IA
                    const blocks = await editor.tryParseMarkdownToBlocks(answer);
                    editor.insertBlocks(blocks, editor.document[editor.document.length - 1].id);
                }
            } else {
                // Pas de contenu existant, simplement insérer la réponse de l'IA
                const blocks = await editor.tryParseMarkdownToBlocks(answer);
                editor.insertBlocks(blocks, editor.document[editor.document.length - 1].id);
            }
            editor.focus();
        }

        return answer;
    };

    return { requestAIAnswer, isPending };
};