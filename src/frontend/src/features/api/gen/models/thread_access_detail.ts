/**
 * Generated by orval v7.10.0 🍺
 * Do not edit manually.
 * messages API
 * This is the messages API schema.
 * OpenAPI spec version: 1.0.0 (v1.0)
 */
import type { MailboxLight } from "./mailbox_light";
import type { ThreadAccessRoleChoices } from "./thread_access_role_choices";

/**
 * Serializer for thread access details.
 */
export interface ThreadAccessDetail {
  /** primary key for the record as UUID */
  readonly id: string;
  mailbox: MailboxLight;
  readonly role: ThreadAccessRoleChoices;
}
