/**
 * Generated by orval v7.10.0 🍺
 * Do not edit manually.
 * messages API
 * This is the messages API schema.
 * OpenAPI spec version: 1.0.0 (v1.0)
 */
import type { MailboxRoleChoices } from "./mailbox_role_choices";

/**
 * Serialize mailboxes.
 */
export interface Mailbox {
  /** primary key for the record as UUID */
  readonly id: string;
  readonly email: string;
  readonly role: MailboxRoleChoices;
  readonly count_unread_messages: string;
  readonly count_messages: string;
}
