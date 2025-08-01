/**
 * Generated by orval v7.10.0 🍺
 * Do not edit manually.
 * messages API
 * This is the messages API schema.
 * OpenAPI spec version: 1.0.0 (v1.0)
 */

export type ThreadsListParams = {
  /**
   * Filter threads that have active messages (1=true, 0=false).
   */
  has_active?: number;
  /**
   * Filter threads with attachments (1=true, 0=false).
   */
  has_attachments?: number;
  /**
   * Filter threads with draft messages (1=true, 0=false).
   */
  has_draft?: number;
  /**
   * Filter threads that have messages (1=true, 0=false).
   */
  has_messages?: number;
  /**
   * Filter threads with messages sent by the user (1=true, 0=false).
   */
  has_sender?: number;
  /**
   * Filter threads with starred messages (1=true, 0=false).
   */
  has_starred?: number;
  /**
   * Filter threads that are trashed (1=true, 0=false).
   */
  has_trashed?: number;
  /**
   * Filter threads that are spam (1=true, 0=false).
   */
  is_spam?: number;
  /**
   * Filter threads by label slug.
   */
  label_slug?: string;
  /**
   * Filter threads by mailbox ID.
   */
  mailbox_id?: string;
  /**
   * A page number within the paginated result set.
   */
  page?: number;
  /**
   * Search threads by content (subject, sender, recipients, message body).
   */
  search?: string;
};
