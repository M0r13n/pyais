##################################
SOTDMA / ITDMA communication state
##################################

Certain message types (1,2,4,9,18) contain diagnostic information for the radio system.
This information is encoded in up to 20 bits of data in the `radio` field and is 
used in planning for the next transmission in order to avoiding mutual interference.

There are two different communication states used in AIS messages:

1. **SOTDMA**: contains information used by the slot allocation algorithm in the SOTDMA concept
2. **ITDMA**: contains information used by the slot allocation algorithm in the ITDMA concept

The concrete details of these concepts are out of the scope oh this document.
Your may refer to [ITU-R M.1371-1 ](https://www.itu.int/dms_pubrec/itu-r/rec/m/R-REC-M.1371-1-200108-S!!PDF-E.pdf).

**pyais** offers the following methods:

.. py:function:: get_communication_state()

   Return the communication state decoded from the `radio` field.

   :return: A dictionary containing the decoded data. Not all fields
            are set. Some default to `None`
   :rtype: Dict[str, Optional[int]]


.. py:function:: is_sotdma

   Return True if the communication state contains SOTDMA data

   :rtype: bool


.. py:function:: is_itdma

   Return True if the communication state contains ITDMA data

   :rtype: bool
