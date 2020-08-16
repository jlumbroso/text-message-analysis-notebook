"""
Library to assist in loading CSV exports from the PhoneView macOS app, which
allows the extraction of data from an iPhone, including (but not exclusively)
several different varieties of text messages: SMS, iMessage and WhatsApp.
"""


__version__ = "1.0.0"
__author__ = "Jérémie Lumbroso <lumbroso@cs.princeton.edu>"

__all__ = [
    "PhoneViewMsgData",
    "load_csv",
    "erase_labels",
]


# Standard Python library
import collections
import csv
import datetime
import enum
import io
import re
import textwrap
import typing

# Pandas library: May need to be installed
try:
    import pandas as pd
except ImportError as err:
    err.message = textwrap.dedent(
        """
        You are missing the `pandas` package. Install it before proceeding.
    
        See: https://pandas.pydata.org/pandas-docs/stable/getting_started/install.html
    
        Original error message:
            {original_msg}
        """.format(original_msg=err.message))


# Some hard-coded constants

DEFAULT_PHONE_REGION = "US"

# Some hard-coded constants having to do with the PhoneView file format

PHONEVIEW_INTERNAL_DB_FIELDS = ["id", "date", "address", "text", "flags"]
PHONEVIEW_INTERNAL_RECEIVED = "2"
PHONEVIEW_INTERNAL_SENT = "3"
PHONEVIEW_EXTERNAL_RECEIVED = "Received"

# The elementary record type for an entry of PhoneView message log

PhoneViewMsgData = typing.TypedDict(
    "PhoneViewMsgData",
    {
        "timestamp": datetime.datetime,
        "inbound":   bool,
        "length":    int,
        "content":   str,
        "number":    str,
        "name":      str,
        "type":      str,
    },
    total=False
)


class PlotStyle(enum.Enum):
    COUNT = 'count'
    VOLUME = 'volume'


def _load_internal_phoneview_msg_file(
        raw_rows: typing.List[typing.List[str]],
        header: typing.List[str]
) -> typing.List[PhoneViewMsgData]:

    records = []
    
    for row in raw_rows:
        row_dict = dict(zip(header, row))
        
        record = collections.OrderedDict()
        
        if "date" in row_dict:
            # the timestamp is in Unix format
            timestamp = int(row_dict["date"])
            record["timestamp"] = datetime.datetime.fromtimestamp(timestamp)
        
        if "flags" in row_dict:
            record["inbound"] = (row_dict["flags"] == PHONEVIEW_INTERNAL_RECEIVED)
        
        text = row_dict.get("text", "")
        record["length"] = len(text)
        record["content"] = text
        
        if "address" in row_dict:
            record["number"] = row_dict["address"]
        
        if "grouptitle" in row_dict and row_dict.get("grouptitle") != "":
            record["name"] = row_dict["grouptitle"]
        
        records.append(record)
    
    return records


def _load_external_phoneview_msg_file(
        raw_rows: typing.List[typing.List[str]]
) -> typing.List[PhoneViewMsgData]:

    records = []

    for row in raw_rows:
        # Message has this format (last row is missing from old versions):
        # ['Received',
        #  'Nov 11, 2012 15:34:01 PM',
        #  'Alexandra Jovez',
        #  '+16095552144',
        #  "What did you end up getting?.",
        #  "iMessage"]

        timestamp = datetime.datetime.strptime(row[1], "%b %d, %Y %H:%M:%S %p")

        inbound = (row[0] == PHONEVIEW_EXTERNAL_RECEIVED)

        record = collections.OrderedDict({
            "timestamp": timestamp,
            "inbound": inbound,
            "length": len(row[4]),
            "content": row[4],
            "name": row[2],
            "number": row[3],
            "type": row[5] if len(row) >= 5 else "",
        })

        records.append(record)

    return records


def _normalize_phone_number(phone_number: typing.Union[str, int]) -> str:
    try:
        # using a dedicated package if available
        # see: https://github.com/daviddrysdale/python-phonenumbers
        import phonenumbers
        normalized_phone_number = phonenumbers.format_number(
            numobj=phonenumbers.parse(
                number=phone_number,
                region=DEFAULT_PHONE_REGION,
            ),
            num_format=phonenumbers.PhoneNumberFormat.E164)

    except ImportError:
        if phone_number is int:
            normalized_phone_number = str(phone_number)
        else:
            normalized_phone_number = phone_number
            for c in " ()-+":
                normalized_phone_number = normalized_phone_number.replace(c, "")

    return normalized_phone_number


# noinspection PyBroadException
def _compare_phone_numbers(
        *phone_numbers: typing.Union[str, int]
) -> bool:
    try:
        return len(set(map(_normalize_phone_number, phone_numbers))) == 1
    except:
        return False


def load_csv(
        filepath: str,
        phone_number: typing.Optional[str] = None,
        keep_type: bool = True,
        keep_other_identity: bool = False
) -> pd.DataFrame:

    # read CSV file using standard Python library
    with open(filepath, "r") as csv_file:
        csv_reader = csv.reader(csv_file,
                                delimiter=',',
                                quotechar='"',
                                quoting=csv.QUOTE_ALL)
        raw_rows = [row for row in csv_reader]

    if len(raw_rows) == 0:
        return

    # if the first row contains headers, and coincides with internal
    # field names, then we have a file in the internal format
    if len(set(raw_rows[0]).intersection(set(PHONEVIEW_INTERNAL_DB_FIELDS))) > 1:

        header = raw_rows[0]

        records = _load_internal_phoneview_msg_file(
            raw_rows=raw_rows[1:],
            header=header,
        )

    else:
        records = _load_external_phoneview_msg_file(
            raw_rows=raw_rows
        )

    # post process
    post_processed_records = []

    for record in records:

        # if user requested records for specific number, skip record if not
        # from that number
        if phone_number is not None and "number" in record:
            if not _compare_phone_numbers(record["number"], phone_number):
                continue

        # if user wants name/number dropped, remove from record
        if not keep_other_identity:
            if "name" in record:
                del record["name"]
            if "number" in record:
                del record["number"]

        if not keep_type and "type" in record:
            del record["type"]

        post_processed_records.append(record)

    if len(post_processed_records) == 0:
        return

    # sort chronologically by timestamp
    post_processed_records = sorted(
        post_processed_records,
        key=lambda record: record["timestamp"]
    )

    # create the pandas dataframe, index by timestamp and sort chronologically
    df = pd.DataFrame(post_processed_records)
    df = df.set_index("timestamp")
    df = df.sort_index(ascending=True)

    return df


def erase_labels(lst, regexp=r"([0-9]*)/[0-9]*"):

    # default regexp, saves first number
    if regexp is None:
        regexp = r"([0-9]*)/[0-9]*"

    cregexp = re.compile(regexp)

    new_lst = []
    prev_new_item = None

    for item in lst:
        new_item = ""

        m = cregexp.search(item)
        if m is not None:
            new_item = "".join(m.groups())
            if new_item == prev_new_item:
                new_item = ""
            else:
                prev_new_item = new_item

        new_lst.append(new_item)

    return new_lst


def dump_to_csv(dataframe: pd.DataFrame, filepath: str = None) -> typing.Optional[str]:
    # make sure we have the timestamp
    if dataframe.index.name is not None:
        dataframe = dataframe.reset_index()

    header = dataframe.columns.to_list()

    record_list = list()

    for row_id, row in enumerate(dataframe.values.tolist()):
        row_dict = dict(zip(header, row))

        record = collections.OrderedDict({
            "id": row_id,
            "date": int(row_dict["timestamp"].to_pydatetime().timestamp()),
            "address": row_dict.get("number", ""),
            "text": row_dict.get("content", ""),
            "flags": (
                PHONEVIEW_INTERNAL_RECEIVED if row_dict["inbound"]
                else PHONEVIEW_INTERNAL_SENT),
        })

        record_list.append(record)

    if filepath is not None:
        f = open(filepath, "w", newline="")

    else:
        f = io.StringIO(newline="")

    field_names = list(record_list[0].keys())
    writer = csv.DictWriter(
        f,
        fieldnames=field_names,
        delimiter=',',
        quotechar='"',
        quoting=csv.QUOTE_ALL)

    writer.writeheader()
    writer.writerows(record_list)

    if filepath is not None:
        return

    else:
        return f.getvalue()


def plot_texts(
        texts_df: pd.DataFrame,
        time_frequency: str = "M",
        split_by_direction: bool = True,
        absolute: bool = True,
        remove_gaps: bool = False,
        count_or_volume: PlotStyle = PlotStyle.COUNT,
        label_date_format=None,
        colors=None,
):

    df = texts_df

    def aggregate_df(df):
        if count_or_volume == PlotStyle.COUNT:
            agg_df = df.resample(time_frequency).count().drop(columns=["length", "content"])
        elif count_or_volume == PlotStyle.VOLUME:
            agg_df = df.resample(time_frequency).sum().drop(columns=["inbound"])
        else:
            raise ValueError("{} is not a valid value for `count_or_volume`".format(
                count_or_volume,
            ))

        column_name = agg_df.columns.to_list()[0]

        if remove_gaps:
            agg_df = agg_df[agg_df[column_name] > 0]

        return agg_df


    if split_by_direction:

        # split by inbound/outbound
        df_inbound = df[df["inbound"] == True]
        df_outbound = df[df["inbound"] == False]

        # stack the two datasets
        processed_df = pd.merge(
            aggregate_df(df_inbound),
            aggregate_df(df_outbound),
            how="outer",
            on=["timestamp"]
        )

        # rename columns
        processed_df.rename(columns={"inbound_x": "received", "inbound_y": "sent"}, inplace=True)
        processed_df.rename(columns={"length_x": "received", "length_y": "sent"}, inplace=True)

    else:
        processed_df = aggregate_df(df)

    if absolute:
        processed_df = processed_df.div(processed_df.sum(1), axis=0)

    # compute the title based on the parameters
    title = "Absolute " if absolute else "Relative "
    title += "Number of " if count_or_volume == "count" else "Volume of "
    title += "Messages"
    if split_by_direction:
        title += " (by direction)"

    # actually plot this data
    ax = processed_df.plot(
        kind="bar",
        stacked=True,
        figsize=(12, 5),
        title=title,
        color=colors,
    )

    _ = ax.set_xlabel("Date")
    _ = ax.set_xticklabels(
        erase_labels([
            pandas_datetime.strftime("%Y/%m/%d %H:%m")
            for pandas_datetime in processed_df.index
        ], regexp=label_date_format))

    return ax.get_figure()
