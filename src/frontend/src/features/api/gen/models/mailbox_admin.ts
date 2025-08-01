/**
 * Generated by orval v7.10.0 🍺
 * Do not edit manually.
 * messages API
 * This is the messages API schema.
 * OpenAPI spec version: 1.0.0 (v1.0)
 */
import type { MailboxAccessNestedUser } from "./mailbox_access_nested_user";

/**
 * Serialize Mailbox details for admin view, including users with access.
 */
export interface MailboxAdmin {
  /** primary key for the record as UUID */
  readonly id: string;
  readonly local_part: string;
  readonly domain_name: string;
  /** Whether this mailbox identifies a person (i.e. is not an alias or a group) */
  readonly is_identity: boolean;
  /**
   * primary key for the record as UUID
   * @nullable
   */
  readonly alias_of: string | null;
  readonly accesses: readonly MailboxAccessNestedUser[];
  /** date and time at which a record was created */
  readonly created_at: string;
  /** date and time at which a record was last updated */
  readonly updated_at: string;
}
