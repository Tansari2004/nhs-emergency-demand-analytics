// DemandMonth
let
    Encoded = Text.Combine({"XdXLicNQEEXBXLweg/rzpNexGOefxqDFDC4vDw1N7e7r9cgjzueRzyMe75+/LLPNZZ7mZW5zyDjMMD9V91vz61pmm8s8zcvc5pCYL82X5q15a96at+ateWvemrfmrXlr3pq35tE8mkfzaB7No3k0j+bRPJpH82DOA/OdX9cy21zmaV7mNof8NN+pCnNoDs2hOTSH5tAcmkNzaA7NoTk0p+bUnJpTc2pOzak5Nafm1JyaU3NpLs2luTSX5tJcmktzaS7Npbk0t+bW3Jpbc2tuza25Nbfm1tyaW/PSvDQvzUvz0rw0L81L89K8NC/NS/Op2R1MdzDdwXQH0x1MdzD/d/D9Cw=="}),
    Data = Json.Document(Binary.Decompress(Binary.FromText(Encoded, BinaryEncoding.Base64), Compression.Deflate)),
    Rows = Table.FromRows(Data, {"Month"}),
    Typed = Table.TransformColumnTypes(Rows, {{"Month",type date}}, "en-US")
in
    Typed

// MonthlyDemand
let
    Encoded = Text.Combine({"TZdLkiQ5CETv0usYM/GHs7T1/a8xriohtH6JFHLAIf/+/cOL/L/F/y3686lzun6U+e9rIr+kdIV/ojVET8ziVR+VD7ETI1T00Yoh/ktyMa0vdUCckMWMEJIh+Utimelnz1l1gOXKL+d6WucsrpSPjYfQub6E/dPnMDoCVBTZZ9b378/q0zjkq6whJ0bDMz+RHPIrmq3KZR/HGnJECxLOj/S5x06MpQoUsCFHtCJejm8b0KIVW32hA45m6Sug2XN9NYhCRFxwNDN8FsWoHC0ZwKJ6chktmfHKJfhBk2zJjH2pIcZ00NEMknl84jVEbpD7lzcD2ZrZEin5xHzI0UwEucRFD/H7HlRNPdfEuaZQA0jAQ/KEBNhHzkPqkCWMmOc5LdtuAv6YHnI0UBN8GvIz5OimKHaU522Curq5LrHPOYZwF0fgHmMacmRDc+AekYcc2cR4F7vykCObhiR/Sj7kyMaZi7YdDDm6mS4vtM5DshVloU/i+YK6WuOlanlJ6+ZCIl+wDTkaWJk52oDmuBYORV3oqlsIvK5yVmifrWkM4k5eEu200qDjbRzlaEbqDtroVzzYhCUhfU/Qr3hSCSW+kgGnTSUc2lFnfJPTpyE7ExzPYW1uymzIng1pd6s0EJ23tr0lpUIh9hx0vMqkyHc5PoivW/tClrSvoutwCmWBkh90opiVMRfWFY/G46TwKO+RsYm24uy7WH1IF56Uo8Druci7WHWhxbhtdqNTeQLh0GOwm0HZ35C5hc0YdGpvxQKyxXrR9bogzAfMlTmwq285HrwNRefj74hAjdn+xJthvhKmliHO0cLDTpzVL8MDhx0RSRlnogbawjbrUVER9bFSPPdZPyF2UUPNGOYtytLcetHDemLEgsdxkTxn9tDghXmORaDWsJ4boQGX4fB5Q8u5HG23y//2BM/0MNv1HdfWN+vGDFXdRhnN5Pbzyv12NKjHsB4hyMDPRhI2TLpWFjYPVFk+cdorBhrxY8dEH2btewXnFYyFHNaeyME/cfmwrk11OCljQPmw9kUUJywEmVrD2hmJsQbAFnjOnJmSAQ8WHD6sp4o6lgQUzRrN7lxx2kzy1rWOP/oeh+g/4mE9x0N2HAbFGnb0dPgFZghXPHHa34J1DWzFc5/1JPP6+c7eWjbrVodnKOzmju3NesowXo/1IF/WemJq/MzN0mFHT1nJ+0yMr8vurEGdJdLvNGfeacPktBfComHczAo2th94mF090RABIyOMuGHtE74wprDpsAzraU3EqGsP92HaNciyvp3hHNbGafAd6Jn3O+2xzlLUfHo+97WeBZfG6qT+vKH1dIEXIHo9b2g9Dcv1z4Zrl7WeqEvEoZZ43tB6Cpo6tiU8b7j1yfh/sY35eryPnk7iX9DdJnn+mxQ2UNs/0Seu9ZTE+9T9fqePnuaYePCt3oPZn8WR8T5Mh9sPPnrin4XsPz43R/dvCjan3HkI7aWf/dkfkQJoVlga/v0P"}),
    Data = Json.Document(Binary.Decompress(Binary.FromText(Encoded, BinaryEncoding.Base64), Compression.Deflate)),
    Rows = Table.FromRows(Data, {"Month","Admissions","Over 12 hour delays"}),
    Typed = Table.TransformColumnTypes(Rows, {{"Month",type date},{"Admissions",Int64.Type},{"Over 12 hour delays",Int64.Type}}, "en-US")
in
    Typed

// BedQuarter
let
    Encoded = Text.Combine({"VdK5DcAwDMXQXVzHgPTlS7ME2X+NwIWDsGTxOt53kXmvNmpYea6TiXTV8JOjWjD/dtAO2kk7aSftpF20i3bRLtqkTdqkTVgZ7M6f3ZlIWKd1Wqd1WtGKVrSiDdqgDdqgbbSNttE22k7Lr8SvxK/Er/R99bw="}),
    Data = Json.Document(Binary.Decompress(Binary.FromText(Encoded, BinaryEncoding.Base64), Compression.Deflate)),
    Rows = Table.FromRows(Data, {"Quarter end"}),
    Typed = Table.TransformColumnTypes(Rows, {{"Quarter end",type date}}, "en-US")
in
    Typed

// QuarterlyBeds
let
    Encoded = Text.Combine({"TZVLctwwDETv4rWMwp/AWVK+/zXSkEZDahE7VpN6aDbAf/9+lCV+OX+Nfy5h5w6q1aJ2tTIv8oolfrX8Xa+4P2LVJcS9Sv2qZkvCCuZZ+RWL/pqMWHoZVbUYNuOKpFBr7i3OX7aP2FyVlqXmutotnXQwdGPkZjb1ogINy9UmzJTmPCsP8ZeZkykqOwrvWZtQrMlJsZFLkyoKO6lk0mI3jy1dB3CqUOk8AF6CbedBdbzFL7BWY98ssSloqZOM5Qfw2sDc7tSPVdVlTB6Wa50YmxjfJ0DOh2V1kaXclb7aOpDNnBYWCA4scunDXxu5NrI4bGXFIQ4l4/R8TiQ2ch3IICQ4nDG50CwShuMnxZeYAxSaeD+xWBz3f9ZxIH0ggwCBxDOxcJykC57cyH0g4/sECPbH5X4CdSD3gWwLmyGdOpvZWg9ynxjb5YCzk4Uxw9z0aYKdDOXNDM+cbDjunbmpOav3YY/4YW6NaILHdUW5MqnLunO6lQ8wIlaBw0NAr2UG6f27nAQfXHwZ7TGvo6/VgWjWWLxLU3lpO7UXumeiAS18pomJra/Bo/3ALiSTPCWsrtLyRWPvnhQj/dDis/CgYNm60E8GdE6QnAg7EfCaOO5WK6j9cXcHXnW7C7PiTkTPIQvmVU6IdyJG/B0Uk9s3EYqfZNq5ciPrMSigJp9jnfaRwTD45ifGl9kCfXcnfnpJMekaNc3Or9g2s6M2FBiB1+n9GRW+ke1ALkETY5rFJF6QnuVLd4ZH+yVu/SRxcjCBLgmdobkhvsTugHyNndFKuQwObrFv4vTlhGOb6spbAJFVh2++iQPDl0ww3qY8Q6Bn0B3DbcQvsiVORPUOJOxDXZYY9j7mgcZOu33Dp5tQTETWpB6iHGv2qqMV4yiDZxThC4Z+z4QxJY4ZcXfZ9NqefXreiegcKn1VKAszC2XZPU/w73Ecx+1oghyPwXdtib1tRVDsP52QO0r4BulThjlWOdZOauOpbg9zPS5MnQsz5X3uSwj38b5/9LwwzdDYGX0HCxpDnw3qPeCL7x7++w8="}),
    Data = Json.Document(Binary.Decompress(Binary.FromText(Encoded, BinaryEncoding.Base64), Compression.Deflate)),
    Rows = Table.FromRows(Data, {"Quarter end","Available beds","Occupied beds","Quarter days"}),
    Typed = Table.TransformColumnTypes(Rows, {{"Quarter end",type date},{"Available beds",type number},{"Occupied beds",type number},{"Quarter days",Int64.Type}}, "en-US")
in
    Typed

// DimTrust
let
    Encoded = Text.Combine({"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"}),
    Data = Json.Document(Binary.Decompress(Binary.FromText(Encoded, BinaryEncoding.Base64), Compression.Deflate)),
    Rows = Table.FromRows(Data, {"Trust code","Trust","Region code"}),
    Typed = Table.TransformColumnTypes(Rows, {{"Trust code",type text},{"Trust",type text},{"Region code",type text}}, "en-US")
in
    Typed

// TrustSnapshot
let
    Encoded = Text.Combine({"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"}),
    Data = Json.Document(Binary.Decompress(Binary.FromText(Encoded, BinaryEncoding.Base64), Compression.Deflate)),
    Rows = Table.FromRows(Data, {"Trust code","Available beds","Occupied beds"}),
    Typed = Table.TransformColumnTypes(Rows, {{"Trust code",type text},{"Available beds",type number},{"Occupied beds",type number}}, "en-US")
in
    Typed

// ForecastMonth
let
    Encoded = Text.Combine({"Xc6xDYAwDETRXVITyTbxQWaJsv8aUICUn+6ervljlLBo1Xo1L/P46EY6GQvz3eT2nmQjkxR5kTfZQTQnm5PNYrPYLDaLzWKz2Cw262+eDw=="}),
    Data = Json.Document(Binary.Decompress(Binary.FromText(Encoded, BinaryEncoding.Base64), Compression.Deflate)),
    Rows = Table.FromRows(Data, {"Month"}),
    Typed = Table.TransformColumnTypes(Rows, {{"Month",type date}}, "en-US")
in
    Typed

// Forecast
let
    Encoded = Text.Combine({"VZTJjeUwDAVz6bPH4L7E0uj80xiKoi0Y/6Jv2PUoiqXf3x8Ckn+Q/wB/LmUIkksJieKG+i+hdutZzOvRryf+XQNA2ABzkbhULBwXQMQ0b1oLSrn5+uQlHQBuQGUb9nfCC6DG2BUoZUSRPnnJB0APQHPlGQ7Aw2WTkPXO65OXMgCtvxsg4b7yjLS/k4yk+m5tyvD265OXegD7iaRBFoCcdwXimH7bIlnCbOHNSzsAni0gUnYvq+cFAAnm6p0Ck2CRPnnpByAbQEHczUfsCiiig2vhlLdcn7yMA9DpgSLVMZpY7i1oRi84WeQAdl7mAdgMkqbUMbJF7Caao3QTkxRnDt48BDgEnyYkr3NUqrZvQjI0QashN16fQAQ8hJguGGe9TzVCexO18jVK4lnF6PUJRKBDeHRQDRgrmoCr+DXfrALnIGII/BIeH0qczNGiCWEO1b8iONhpZA7hjOMjBKOLjxd7HEuENsq9DtWvTyDCmcfHCCGMGDFaBAig3kXNeL67mECEZyDtKFHq2JjRhGqWbynXRfHWQEPwQ3icYEAdNXoikcPXaZIH21j5BiLEITxScPQ8LDcWATNRawwUKOuK0esTiJCH8FihZjBybCsodHlZLa4ncX0CEeEQRgtmChg7+iwA61hlDQrkquoTiIiH8Hghrjx6tE9Rzd1TDXU7vbsYL5AOYbwQj6Vm69E1cAb0VJORn06OF8iHMF6gh8Xo0TVY/fp+cnnv6DcQUf7+/gM="}),
    Data = Json.Document(Binary.Decompress(Binary.FromText(Encoded, BinaryEncoding.Base64), Compression.Deflate)),
    Rows = Table.FromRows(Data, {"Month","Actual admissions","Seasonal baseline","Expanding forest","Fixed fit forest","Training through","Training rows"}),
    Typed = Table.TransformColumnTypes(Rows, {{"Month",type date},{"Actual admissions",Int64.Type},{"Seasonal baseline",type number},{"Expanding forest",type number},{"Fixed fit forest",type number},{"Training through",type date},{"Training rows",Int64.Type}}, "en-US")
in
    Typed

// Summary
let
    Encoded = Text.Combine({"i45WMjIwMtM1sNA1MFTSgXIsIZzi1MTi/LzEnPikxOLUnMy8VCUdU2NTUwsDPYPYWAA="}),
    Data = Json.Document(Binary.Decompress(Binary.FromText(Encoded, BinaryEncoding.Base64), Compression.Deflate)),
    Rows = Table.FromRows(Data, {"As of month","Forecast month","Preferred method","Next forecast"}),
    Typed = Table.TransformColumnTypes(Rows, {{"As of month",type date},{"Forecast month",type date},{"Preferred method",type text},{"Next forecast",type number}}, "en-US")
in
    Typed
