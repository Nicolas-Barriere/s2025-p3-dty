/**
 * Generated by orval v7.10.0 🍺
 * Do not edit manually.
 * messages API
 * This is the messages API schema.
 * OpenAPI spec version: 1.0.0 (v1.0)
 */

/**
 * Serializer for importing email files.
 */
export interface ImportFileRequest {
  /** UUID of the blob */
  blob: string;
  /** UUID of the recipient mailbox */
  recipient: string;
}
