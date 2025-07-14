# Email Batch Limit Increase

## Change Made
Increased the email processing limit for intelligent search from **50 to 500 emails**.

### File Modified
- `src/backend/chatbot/config.py`
  - Changed `max_emails_per_batch` from 50 to 500

## Impact
This change allows the RAG (Retrieval Augmented Generation) system to:
1. **Index more emails**: Up to 500 emails can now be processed and indexed for intelligent search
2. **Better search coverage**: Users can search across a much larger email dataset
3. **Improved search quality**: More context available for AI-powered email search

## Technical Details
- **Configuration**: `AlbertConfig.max_emails_per_batch = 500`
- **Usage**: Applied in `email_service.py` where it limits the number of emails sent to the RAG system
- **Rate limiting**: Existing batch delay (1 second every 10 emails) prevents API overload
- **Timeout**: 30-second timeout remains adequate for processing larger batches

## Backward Compatibility
- ✅ Fully backward compatible
- ✅ No breaking changes to API
- ✅ Existing indexed emails remain valid
- ✅ Smart reindexing prevents unnecessary reprocessing

## Performance Considerations
- **Indexing time**: Initial indexing may take longer with 500 emails vs 50
- **Memory usage**: Slightly higher memory usage during processing
- **API rate limits**: Batch delays prevent overwhelming the Albert API
- **Smart caching**: Reindexing prevention ensures emails are only processed once

## Expected Benefits
1. **More comprehensive search results**: 10x larger email dataset
2. **Better AI understanding**: More context for intelligent search
3. **Improved user experience**: Better chance of finding relevant emails
4. **Future-proof**: Can handle larger mailboxes effectively
5. **Intelligent filtering**: Dynamic score thresholds ensure only high-quality results are shown
