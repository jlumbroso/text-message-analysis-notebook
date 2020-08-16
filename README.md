# Text Message Analysis Notebook

[This notebook](Text%20Analysis.ipynb) shows how to visualize the number of text
messages exchanged (with a specific person, or overall), and the volume of characters
exchanged.

![Example of the plot of the number of texts
received/sent with a specific person over time](example-absolute-text-count.png)

![Example of the plot of the rescaled number of texts
received/sent with a specific person over time](example-rescaled-text-count.png)

## Rationale

It is surprising to notice how much information can be extracted from the visualization
of the *patterns* of communication alone—without the contents of the messages. For
instance, in the example above, it is clear that the person sending messages (in green)
is more invested in the relationship: In the *rescaled plot*, we can see that in
the beginning, both of the correspondents are responsible for about 50% of the messages;
but this trend quickly changes over time.

## Requirements

- [PhoneView](https://www.ecamm.com/mac/phoneview/): This is the app I recommend to
extract text messages from your iPhone. It is able to handle SMS, iMessage and WhatsApp
seamlessly. It costs $29.95 for a Lifetime License, and has been available and reliable
since 2008—but there is also a trial version that will work for this.

- Jupyter Notebook and `pandas`: These are the tools I use in this notebook to analyze
and plot my text messages.

### For Windows & Android users

For Windows computers, you can use [iExplorer](https://macroplant.com/iexplorer);
for Android phones, you can use the [SMS Backup and Restore
app](https://play.google.com/store/apps/details?id=com.riteshsahu.SMSBackupRestore&hl=en).
Read [this DigitalTrends article](https://www.digitaltrends.com/mobile/how-to-save-text-messages/)
for more information. The notebook provided here may need to be adapted.