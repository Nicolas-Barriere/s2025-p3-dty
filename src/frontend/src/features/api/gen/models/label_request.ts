/**
 * Generated by orval v7.10.0 🍺
 * Do not edit manually.
 * messages API
 * This is the messages API schema.
 * OpenAPI spec version: 1.0.0 (v1.0)
 */

/**
 * Serializer for Label model.
 */
export interface LabelRequest {
  /**
   * Name of the label/folder (can use slashes for hierarchy, e.g. 'Work/Projects')
   * @minLength 1
   * @maxLength 255
   */
  name: string;
  /**
   * Color of the label in hex format (e.g. #FF0000)
   * @minLength 1
   * @maxLength 7
   */
  color?: string;
  /** Mailbox that owns this label */
  mailbox: string;
  /** Threads that have this label */
  threads?: string[];
}
