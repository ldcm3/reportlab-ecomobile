"""
This modules defines a variety of Bar Chart components.

The basic flavors are Side-by-side, stacked and 100% bar charts,
available in horizontal and vertical versions.
"""
#chartparts - candidate components for a chart library.

import string
from types import FunctionType

from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.lib import colors 
from reportlab.graphics.widgetbase import Widget, TypedPropertyCollection
from reportlab.graphics.shapes import *
from reportlab.graphics.charts.textlabels import Label
from reportlab.graphics.charts.axes import XCategoryAxis, YValueAxis
from reportlab.graphics.charts.axes import YCategoryAxis, XValueAxis


### Helpers (maybe put this into Drawing... or shapes)
##
##def grid(group, x, y, width, height, dist=100):
##    "Make a rectangular grid given a distance between two adjacent lines."
##
##    g = group
##
##    # Vertical lines
##    for x0 in range(x, x+width, dist):
##        lineWidth = 0
##        if x0 % 5 == 0:
##            lineWidth = 1
##        g.add(Line(x0, 0, x0, y+height, strokeWidth=lineWidth))
##
##    # Horizontal lines
##    for y0 in range(y, y+height, dist):
##        lineWidth = 0
##        if y0 % 5 == 0:
##            lineWidth = 1
##        g.add(Line(0, y0, x+width, y0, strokeWidth=lineWidth))


# Bar chart classes

class VerticalBarChart(Widget):
    """Bar chart with multiple side-by-side bars.

    Variants will be provided for stacked and 100% charts,
    probably by running all three off a common base class."""

    _attrMap = {
        'debug':isNumber,
        'x':isNumber,
        'y':isNumber,
        'width':isNumber,
        'height':isNumber,

        'useAbsolute':isNumber,
        'barWidth':isNumber,
        'barLabelNudge':isNumber,
        'groupSpacing':isNumber,
        'barSpacing':isNumber,

        'strokeColor':isColorOrNone,
        'fillColor':isColorOrNone,

        'defaultColors':SequenceOf(isColor),

        'categoryAxis':None,
        'categoryNames':isListOfStrings,
        'valueAxis':None,
        'data':None,
        'barLabels':None,
        'barLabelFormat':None
        }

    def __init__(self):
        self.debug = 0

        self.x = 0
        self.y = 0
        self.width = 200
        self.height = 100

        # allow for a bounding rectangle
        self.strokeColor = None
        self.fillColor = None

        # named so we have less recoding for the horizontal one :-)
        self.categoryAxis = XCategoryAxis()
        self.valueAxis = YValueAxis()

        # this defines two series of 3 points.  Just an example.
        self.data = [(100,110,120,130),
                     (70, 80, 80, 90)]        
        self.categoryNames = ('North','South','East','West')
        # we really need some well-designed default lists of
        # colors e.g. from Tufte.  These will be used in a
        # cycle to set the fill color of each series.
        self.defaultColors = [colors.red, colors.green, colors.blue]

        # control bar spacing. is useAbsolute = 1 then
        # the next parameters are in points; otherwise
        # they are 'proportions' and are normalized to
        # fit the available space.  Half a barSpacing
        # is allocated at the beginning and end of the
        # chart.
        self.useAbsolute = 0   #- not done yet
        self.barWidth = 10
        self.groupSpacing = 5
        self.barSpacing = 0

        self.barLabels = TypedPropertyCollection(Label)
        self.barLabelFormat = None

        # this says whether the origin is inside or outside
        # the bar - +10 means put the origin ten points
        # above the tip of the bar if value > 0, or ten
        # points inside if bar value < 0.  This is different
        # to label dx/dy which are not dependent on the
        # sign of the data.
        self.barLabelNudge = 0
        # if you have multiple series, by default they butt
        # together.


    def demo(self):
        """Shows basic use of a bar chart"""

        drawing = Drawing(200, 100)

        data = [
                (13, 5, 20, 22, 37, 45, 19, 4),
                (14, 6, 21, 23, 38, 46, 20, 5)
                ]
        
        bc = VerticalBarChart()
        bc.x = 20
        bc.y = 10
        bc.height = 85
        bc.width = 180
        bc.data = data

        drawing.add(bc)

        return drawing


    def _findMinMaxValues(self):
        """Find the minimum and maximum value of the data we have."""

        data = self.data
        m, M = Auto, Auto
        for row in data:
            for val in row:
                if val < m:
                    m = val
                if val > M:
                    M = val

        return m, M
    

    def calcBarPositions(self):
        """Works out where they go.

        Sets an attribute _barPositions which is a list of
        lists of (x, y, width, height) matching the data."""

        self._seriesCount = len(self.data)
        self._rowLength = len(self.data[0])
        
        if self.useAbsolute:
            # bar dimensions are absolute
            normFactor = 1.0
        else:
            # bar dimensions are normalized to fit.  How wide
            # notionally is one group of bars?
            normWidth = (self.groupSpacing 
                        + (self._seriesCount * self.barWidth) 
                        + ((self._seriesCount - 1) * self.barSpacing)
                        )
            availWidth = self.categoryAxis.scale(0)[1]
            normFactor = availWidth / normWidth
            if self.debug:
                print '%d series, %d points per series' % (self._seriesCount, self._rowLength)
                print 'width = %d group + (%d bars * %d barWidth) + (%d gaps * %d interBar) = %d total' % (
                    self.groupSpacing, self._seriesCount, self.barWidth,
                    self._seriesCount - 1, self.barSpacing, normWidth)

        self._barPositions = []
        for rowNo in range(len(self.data)):
            barRow = []
            for colNo in range(len(self.data[0])):
                datum = self.data[rowNo][colNo]

                # Ufff...
                if self.useAbsolute:
                    groupX = len(self.data) * self.barWidth + \
                             len(self.data) * self.barSpacing + \
                             self.groupSpacing
                    groupX = groupX * colNo + 0.5 * self.groupSpacing + self.x
                    x = groupX + rowNo * (self.barWidth + self.barSpacing)
                else:
                    (groupX, groupWidth) = self.categoryAxis.scale(colNo)
                    x = groupX + normFactor * (0.5 * self.groupSpacing \
                                               + rowNo * (self.barWidth + self.barSpacing))
                width = self.barWidth * normFactor

                # 'Baseline' correction...
                scale = self.valueAxis.scale
                vm, vM = self.valueAxis.valueMin, self.valueAxis.valueMax
                if Auto in (vm, vM):
                    y = scale(self._findMinMaxValues()[0])
                elif vm <= 0 <= vM:
                    y = scale(0)
                elif 0 < vm:
                    y = scale(vm)
                elif vM < 0:
                    y = scale(vM)

                height = self.valueAxis.scale(datum) - y
                barRow.append((x, y, width, height))
                    
            self._barPositions.append(barRow)
        

    def draw(self):
        self.valueAxis.configure(self.data)
        self.valueAxis.setPosition(self.x, self.y, self.height)

        # if zero is in chart, put x axis there, otherwise
        # use bottom.
        xAxisCrossesAt = self.valueAxis.scale(0)
        if ((xAxisCrossesAt > self.y + self.height) or (xAxisCrossesAt < self.y)):
            self.categoryAxis.setPosition(self.x, self.y, self.width)
        else:
            self.categoryAxis.setPosition(self.x, xAxisCrossesAt, self.width)

        self.categoryAxis.configure(self.data)
        
        self.calcBarPositions()        
        
        g = Group()

        # debug mode - show border
        g.add(Rect(self.x, self.y,
                   self.width, self.height,
                   strokeColor = self.strokeColor,
                   fillColor= self.fillColor))
        
        g.add(self.categoryAxis)
        g.add(self.valueAxis)

        labelFmt = self.barLabelFormat

        for rowNo in range(len(self._barPositions)):
            row = self._barPositions[rowNo]
            colorCount = len(self.defaultColors)
            colorIdx = rowNo % colorCount
            rowColor = self.defaultColors[colorIdx]
            for colNo in range(len(row)):
                barPos = row[colNo]
                (x, y, width, height) = barPos
                r = Rect(x, y, width, height)
                r.fillColor = rowColor
                r.strokeColor = colors.black
                g.add(r)

                if labelFmt is None:
                    labelText = None
                elif type(labelFmt) is StringType:
                    labelText = labelFmt % self.data[rowNo][colNo]
                elif type(labelFmt) is FunctionType:
                    labelText = labelFmt(self.data[rowNo][colNo])
                else:
                    raise Exception, "Unknown formatter type %s, expected string or function" % labelFmt

                # We currently overwrite the boxAnchor with 'c' and display
                # it at a constant offset to the bar's top/bottom determined
                # by the barLabelNudge attribute.
                if labelText:
                    label = self.barLabels[(rowNo, colNo)]
                    labelWidth = stringWidth(labelText, label.fontName, label.fontSize)                    

                    sign = lambda v:[-1, 1][v>=0] # Where the heck is this function??
                    y0 = y + height + sign(height) * self.barLabelNudge
                    x0 = x + 0.5*width
                    label.boxAnchor = 'c' # saves a lot of correcting code like this:...
##                    if label.boxAnchor in ('w', 'sw', 'nw'):
##                        x0 = x0 - 0.5*labelWidth
##                    elif label.boxAnchor in ('e', 'se', 'ne'):
##                        x0 = x0 + 0.5*labelWidth
##                    elif label.boxAnchor == 'c':
##                        pass
                    label.setOrigin(x0, y0)
                    label.setText(labelText)

                    g.add(label)

        return g
        

class HorizontalBarChart(Widget):
    """Bar chart with multiple side-by-side bars.

    Variants will be provided for stacked and 100% charts,
    probably by running all three off a common base class."""

    _attrMap = {
        'debug':isNumber,
        'x':isNumber,
        'y':isNumber,
        'width':isNumber,
        'height':isNumber,

        'useAbsolute':isNumber,
        'barWidth':isNumber,
        'barLabelNudge':isNumber,
        'groupSpacing':isNumber,
        'barSpacing':isNumber,

        'strokeColor':isColorOrNone,
        'fillColor':isColorOrNone,

        'defaultColors':SequenceOf(isColor),

        'categoryAxis':None,
        'categoryNames':isListOfStrings,
        'valueAxis':None,
        'data':None,
        'barLabels':None,
        'barLabelFormat':None
        }

    def __init__(self):
        self.debug = 0

        self.x = 0
        self.y = 0
        self.width = 200
        self.height = 100

        # allow for a bounding rectangle
        self.strokeColor = None
        self.fillColor = None

        # named so we have less recoding for the horizontal one :-)
        self.categoryAxis = YCategoryAxis()
        self.valueAxis = XValueAxis()

        # this defines two series of 3 points.  Just an example.
        self.data = [(100,110,120,130),
                     (70, 80, 80, 90)]        
        self.categoryNames = ('North','South','East','West')
        # we really need some well-designed default lists of
        # colors e.g. from Tufte.  These will be used in a
        # cycle to set the fill color of each series.
        self.defaultColors = [colors.red, colors.green, colors.blue]

        # control bar spacing. is useAbsolute = 1 then
        # the next parameters are in points; otherwise
        # they are 'proportions' and are normalized to
        # fit the available space.  Half a barSpacing
        # is allocated at the beginning and end of the
        # chart.
        self.useAbsolute = 0   #- not done yet
        self.barWidth = 10
        self.groupSpacing = 5
        self.barSpacing = 0

        self.barLabels = TypedPropertyCollection(Label)
        self.barLabelFormat = None

        # this says whether the origin is inside or outside
        # the bar - +10 means put the origin ten points
        # above the tip of the bar if value > 0, or ten
        # points inside if bar value < 0.  This is different
        # to label dx/dy which are not dependent on the
        # sign of the data.
        self.barLabelNudge = 0
        # if you have multiple series, by default they butt
        # together.


    def demo(self):
        """Shows basic use of a bar chart"""

        drawing = Drawing(200, 100)

        data = [
                (13, 5, 20, 22, 37, 45, 19, 4),
                (14, 6, 21, 23, 38, 46, 20, 5)
                ]
        
        bc = HorizontalBarChart()
        bc.x = 10
        bc.y = 10
        bc.height = 85
        bc.width = 180
        bc.data = data

        drawing.add(bc)

        return drawing


    def _findMinMaxValues(self):
        """Find the minimum and maximum value of the data we have."""

        data = self.data
        m, M = Auto, Auto
        for row in data:
            for val in row:
                if val < m:
                    m = val
                if val > M:
                    M = val

        return m, M
    

    def calcBarPositions(self):
        """Works out where they go.

        Sets an attribute _barPositions which is a list of
        lists of (x, y, width, height) matching the data."""

        self._seriesCount = len(self.data)
        self._rowLength = len(self.data[0])
        
        if self.useAbsolute:
            # bar dimensions are absolute
            normFactor = 1.0
        else:
            # bar dimensions are normalized to fit.  How wide
            # notionally is one group of bars?
            normWidth = (self.groupSpacing 
                        + (self._seriesCount * self.barWidth) 
                        + ((self._seriesCount - 1) * self.barSpacing)
                        )
            availWidth = self.categoryAxis.scale(0)[1]
            normFactor = availWidth / normWidth
            if self.debug:
                print '%d series, %d points per series' % (self._seriesCount, self._rowLength)
                print 'width = %d group + (%d bars * %d barWidth) + (%d gaps * %d interBar) = %d total' % (
                    self.groupSpacing, self._seriesCount, self.barWidth,
                    self._seriesCount - 1, self.barSpacing, normWidth)
        
        self._barPositions = []
        for rowNo in range(len(self.data)):
            barRow = []
            for colNo in range(len(self.data[0])):
                datum = self.data[rowNo][colNo]

                # Ufff...
                if self.useAbsolute:
                    groupY = len(self.data) * self.barWidth + \
                             len(self.data) * self.barSpacing + \
                             self.groupSpacing
                    groupY = groupY * colNo + 0.5 * self.groupSpacing + self.y
                    y = groupY + rowNo * (self.barWidth + self.barSpacing)
                else:
                    (groupY, groupWidth) = self.categoryAxis.scale(colNo)
                    y = groupY + normFactor * (0.5 * self.groupSpacing \
                                               + rowNo * (self.barWidth + self.barSpacing))
                height = self.barWidth * normFactor

                # 'Baseline' correction...
                scale = self.valueAxis.scale
                vm, vM = self.valueAxis.valueMin, self.valueAxis.valueMax
                if Auto in (vm, vM):
                    x = scale(self._findMinMaxValues()[0])
                elif vm <= 0 <= vM:
                    x = scale(0)
                elif 0 < vm:
                    x = scale(vm)
                elif vM < 0:
                    x = scale(vM)

                width = self.valueAxis.scale(datum) - x
                barRow.append((x, y, width, height))

            self._barPositions.append(barRow)
        

    def draw(self):
        self.valueAxis.configure(self.data)
        self.valueAxis.setPosition(self.x, self.y, self.width)

        # if zero is in chart, put y axis there, otherwise
        # use left.
        yAxisCrossesAt = self.valueAxis.scale(0)            
        if ((yAxisCrossesAt > self.x + self.width) or (yAxisCrossesAt < self.x)):
            self.categoryAxis.setPosition(self.x, self.y, self.height)
        else:
            self.categoryAxis.setPosition(yAxisCrossesAt, self.y, self.height)

        self.categoryAxis.configure(self.data)

        self.calcBarPositions()                

        g = Group()

        # debug mode - show border
        g.add(Rect(self.x, self.y,
                   self.width, self.height,
                   strokeColor = self.strokeColor,
                   fillColor= self.fillColor))
        
        g.add(self.categoryAxis)
        g.add(self.valueAxis)

        labelFmt = self.barLabelFormat
        
        for rowNo in range(len(self._barPositions)):
            row = self._barPositions[rowNo]
            colorCount = len(self.defaultColors)
            colorIdx = rowNo % colorCount
            rowColor = self.defaultColors[colorIdx]
            for colNo in range(len(row)):
                barPos = row[colNo]
                (x, y, width, height) = barPos
                r = Rect(x, y, width, height)
                r.fillColor = rowColor
                r.strokeColor = colors.black
                g.add(r)

                if labelFmt is None:
                    labelText = None
                elif type(labelFmt) is StringType:
                    labelText = labelFmt % self.data[rowNo][colNo]
                elif type(labelFmt) is FunctionType:
                    labelText = labelFmt(self.data[rowNo][colNo])
                else:
                    raise Exception, "Unknown formatter type %s, expected string or function" % labelFmt

                # We currently overwrite the boxAnchor with 'c' and display
                # it at a constant offset to the bar's top/bottom determined
                # by the barLabelNudge attribute.
                if labelText:
                    label = self.barLabels[(rowNo, colNo)]
                    labelWidth = stringWidth(labelText, label.fontName, label.fontSize)                    

                    sign = lambda v:[-1, 1][v>=0] # Where the heck is this function??
                    x0 = x + width + sign(width) * self.barLabelNudge
                    y0 = y + 0.5*height
                    label.boxAnchor = 'c'
                    label.setOrigin(x0, y0)
                    label.setText(labelText)

                    g.add(label)

        return g


# Vertical samples.

def sampleV0a():
    "A slightly pathologic bar chart with only TWO data items."
    
    drawing = Drawing(400, 200)

    data = [(13, 20)]
    
    bc = VerticalBarChart()
    bc.x = 50
    bc.y = 50
    bc.height = 125
    bc.width = 300
    bc.data = data

    bc.strokeColor = colors.black

    bc.valueAxis.valueMin = 0
    bc.valueAxis.valueMax = 60
    bc.valueAxis.valueStep = 15
    
    bc.categoryAxis.labels.boxAnchor = 'ne'
    bc.categoryAxis.labels.dx = 8
    bc.categoryAxis.labels.dy = -2
    bc.categoryAxis.labels.angle = 30
    bc.categoryAxis.categoryNames = ['Ying', 'Yang']

    drawing.add(bc)

    return drawing    

    
def sampleV0b():
    "A pathologic bar chart with only ONE data item."
    
    drawing = Drawing(400, 200)

    data = [(42,)]
    
    bc = VerticalBarChart()
    bc.x = 50
    bc.y = 50
    bc.height = 125
    bc.width = 300
    bc.data = data
    bc.strokeColor = colors.black

    bc.valueAxis.valueMin = 0
    bc.valueAxis.valueMax = 50
    bc.valueAxis.valueStep = 15
    
    bc.categoryAxis.labels.boxAnchor = 'ne'
    bc.categoryAxis.labels.dx = 8
    bc.categoryAxis.labels.dy = -2
    bc.categoryAxis.labels.angle = 30
    bc.categoryAxis.categoryNames = ['Jan-99']

    drawing.add(bc)

    return drawing    

    
def sampleV0c():
    "A really pathologic bar chart with NO data items at all!"
    
    drawing = Drawing(400, 200)

    data = [()]
    
    bc = VerticalBarChart()
    bc.x = 50
    bc.y = 50
    bc.height = 125
    bc.width = 300
    bc.data = data
    bc.strokeColor = colors.black

    bc.valueAxis.valueMin = 0
    bc.valueAxis.valueMax = 60
    bc.valueAxis.valueStep = 15
    
    bc.categoryAxis.labels.boxAnchor = 'ne'
    bc.categoryAxis.labels.dx = 8
    bc.categoryAxis.labels.dy = -2
    bc.categoryAxis.categoryNames = []

    drawing.add(bc)

    return drawing    

    
def sampleV1():
    "Sample of multi-series bar chart."

    drawing = Drawing(400, 200)

    data = [
            (13, 5, 20, 22, 37, 45, 19, 4),
            (14, 6, 21, 23, 38, 46, 20, 5)
            ]
    
    bc = VerticalBarChart()
    bc.x = 50
    bc.y = 50
    bc.height = 125
    bc.width = 300
    bc.data = data
    bc.strokeColor = colors.black

    bc.valueAxis.valueMin = 0
    bc.valueAxis.valueMax = 60
    bc.valueAxis.valueStep = 15
    
    bc.categoryAxis.labels.boxAnchor = 'ne'
    bc.categoryAxis.labels.dx = 8
    bc.categoryAxis.labels.dy = -2
    bc.categoryAxis.labels.angle = 30

    catNames = string.split('Jan Feb Mar Apr May Jun Jul Aug', ' ')
    catNames = map(lambda n:n+'-99', catNames)
    bc.categoryAxis.categoryNames = catNames
    drawing.add(bc)

    return drawing    

    
def sampleV2a():
    "Sample of multi-series bar chart."
    
    data = [(2.4, -5.7, 2, 5, 9.2),
            (0.6, -4.9, -3, 4, 6.8)
            ]

    labels = ("Q3 2000", "Year to Date", "12 months",
              "Annualised\n3 years", "Since 07.10.99")

    drawing = Drawing(400, 200)

    bc = VerticalBarChart()
    bc.x = 50
    bc.y = 50
    bc.height = 120
    bc.width = 300
    bc.data = data

    bc.barSpacing = 0
    bc.groupSpacing = 10
    bc.barWidth = 10
    
    bc.valueAxis.valueMin = -15
    bc.valueAxis.valueMax = +15
    bc.valueAxis.valueStep = 5
    bc.valueAxis.labels.fontName = 'Helvetica'
    bc.valueAxis.labels.fontSize = 8    
    bc.valueAxis.labels.boxAnchor = 'n'   # irrelevant (becomes 'c')
    bc.valueAxis.labels.textAnchor = 'middle'

    bc.categoryAxis.categoryNames = labels
    bc.categoryAxis.labels.fontName = 'Helvetica'
    bc.categoryAxis.labels.fontSize = 8
    bc.categoryAxis.labels.dy = -60
    
    drawing.add(bc)    

    return drawing


def sampleV2b():
    "Sample of multi-series bar chart."

    data = [(2.4, -5.7, 2, 5, 9.2),
            (0.6, -4.9, -3, 4, 6.8)
            ]

    labels = ("Q3 2000", "Year to Date", "12 months",
              "Annualised\n3 years", "Since 07.10.99")

    drawing = Drawing(400, 200)

    bc = VerticalBarChart()
    bc.x = 50
    bc.y = 50
    bc.height = 120
    bc.width = 300
    bc.data = data

    bc.barSpacing = 5
    bc.groupSpacing = 10
    bc.barWidth = 10
    
    bc.valueAxis.valueMin = -15
    bc.valueAxis.valueMax = +15
    bc.valueAxis.valueStep = 5
    bc.valueAxis.labels.fontName = 'Helvetica'
    bc.valueAxis.labels.fontSize = 8    
    bc.valueAxis.labels.boxAnchor = 'n'   # irrelevant (becomes 'c')
    bc.valueAxis.labels.textAnchor = 'middle'

    bc.categoryAxis.categoryNames = labels
    bc.categoryAxis.labels.fontName = 'Helvetica'
    bc.categoryAxis.labels.fontSize = 8
    bc.categoryAxis.labels.dy = -60
    
    drawing.add(bc)    

    return drawing


def sampleV2c():
    "Sample of multi-series bar chart."

    data = [(2.4, -5.7, 2, 5, 9.99),
            (0.6, -4.9, -3, 4, 9.99)
            ]

    labels = ("Q3 2000", "Year to Date", "12 months",
              "Annualised\n3 years", "Since 07.10.99")

    drawing = Drawing(400, 200)

    bc = VerticalBarChart()
    bc.x = 50
    bc.y = 50
    bc.height = 120
    bc.width = 300
    bc.data = data

    bc.barSpacing = 2
    bc.groupSpacing = 10
    bc.barWidth = 10
    
    bc.valueAxis.valueMin = -15
    bc.valueAxis.valueMax = +15
    bc.valueAxis.valueStep = 5
    bc.valueAxis.labels.fontName = 'Helvetica'
    bc.valueAxis.labels.fontSize = 8    

    bc.categoryAxis.categoryNames = labels
    bc.categoryAxis.labels.fontName = 'Helvetica'
    bc.categoryAxis.labels.fontSize = 8
    bc.valueAxis.labels.boxAnchor = 'n'
    bc.valueAxis.labels.textAnchor = 'middle'
    bc.categoryAxis.labels.dy = -60

    bc.barLabelNudge = 10
    
    bc.barLabelFormat = '%0.2f'
    bc.barLabels.dx = 0
    bc.barLabels.dy = 0
    bc.barLabels.boxAnchor = 'n'  # irrelevant (becomes 'c')
    bc.barLabels.fontName = 'Helvetica'
    bc.barLabels.fontSize = 6

    drawing.add(bc)    

    return drawing


def sampleV3():
    "Faked horizontal bar chart using a vertical real one (deprecated)."

    names = ("UK Equities", "US Equities", "European Equities", "Japanese Equities",
              "Pacific (ex Japan) Equities", "Emerging Markets Equities",
              "UK Bonds", "Overseas Bonds", "UK Index-Linked", "Cash")

    series1 = (-1.5, 0.3, 0.5, 1.0, 0.8, 0.7, 0.4, 0.1, 1.0, 0.3)    
    series2 = (0.0, 0.33, 0.55, 1.1, 0.88, 0.77, 0.44, 0.11, 1.10, 0.33)

    assert len(names) == len(series1), "bad data"
    assert len(names) == len(series2), "bad data"
    
    drawing = Drawing(400, 200)

    bc = VerticalBarChart()
    bc.x = 0
    bc.y = 0
    bc.height = 100
    bc.width = 150
    bc.data = (series1,)
    bc.defaultColors = (colors.green,)

    bc.barLabelFormat = '%0.2f'
    bc.barLabels.dx = 0
    bc.barLabels.dy = 0
    bc.barLabels.boxAnchor = 'w' # irrelevant (becomes 'c')
    bc.barLabels.angle = 90
    bc.barLabels.fontName = 'Helvetica'
    bc.barLabels.fontSize = 6
    bc.barLabelNudge = 10
    
    bc.valueAxis.visible = 0
    bc.valueAxis.valueMin = -2
    bc.valueAxis.valueMax = +2
    bc.valueAxis.valueStep = 1

    bc.categoryAxis.tickUp = 0
    bc.categoryAxis.tickDown = 0
    bc.categoryAxis.categoryNames = names
    bc.categoryAxis.labels.angle = 90
    bc.categoryAxis.labels.boxAnchor = 'w'
    bc.categoryAxis.labels.dx = 0
    bc.categoryAxis.labels.dy = -125
    bc.categoryAxis.labels.fontName = 'Helvetica'
    bc.categoryAxis.labels.fontSize = 6
        
    g = Group(bc)
    g.translate(100, 175)
    g.rotate(-90)
    
    drawing.add(g)    

    return drawing


def sampleV4a():
    "A bar chart showing value axis region starting at *exactly* zero."
    
    drawing = Drawing(400, 200)

    data = [(13, 20)]
    
    bc = VerticalBarChart()
    bc.x = 50
    bc.y = 50
    bc.height = 125
    bc.width = 300
    bc.data = data

    bc.strokeColor = colors.black

    bc.valueAxis.valueMin = 0
    bc.valueAxis.valueMax = 60
    bc.valueAxis.valueStep = 15
    
    bc.categoryAxis.labels.boxAnchor = 'n'
    bc.categoryAxis.labels.dy = -5
    bc.categoryAxis.categoryNames = ['Ying', 'Yang']

    drawing.add(bc)

    return drawing    

    
def sampleV4b():
    "A bar chart showing value axis region starting *below* zero."
    
    drawing = Drawing(400, 200)

    data = [(13, 20)]
    
    bc = VerticalBarChart()
    bc.x = 50
    bc.y = 50
    bc.height = 125
    bc.width = 300
    bc.data = data

    bc.strokeColor = colors.black

    bc.valueAxis.valueMin = -10
    bc.valueAxis.valueMax = 60
    bc.valueAxis.valueStep = 15
    
    bc.categoryAxis.labels.boxAnchor = 'n'
    bc.categoryAxis.labels.dy = -5
    bc.categoryAxis.categoryNames = ['Ying', 'Yang']

    drawing.add(bc)

    return drawing    

    
def sampleV4c():
    "A bar chart showing value axis region staring *above* zero."
    
    drawing = Drawing(400, 200)

    data = [(13, 20)]

    bc = VerticalBarChart()
    bc.x = 50
    bc.y = 50
    bc.height = 125
    bc.width = 300
    bc.data = data

    bc.strokeColor = colors.black

    bc.valueAxis.valueMin = 10
    bc.valueAxis.valueMax = 60
    bc.valueAxis.valueStep = 15
    
    bc.categoryAxis.labels.boxAnchor = 'n'
    bc.categoryAxis.labels.dy = -5
    bc.categoryAxis.categoryNames = ['Ying', 'Yang']

    drawing.add(bc)

    return drawing    


def sampleV4d():
    "A bar chart showing value axis region entirely *below* zero."
    
    drawing = Drawing(400, 200)

    data = [(-13, -20)]

    bc = VerticalBarChart()
    bc.x = 50
    bc.y = 50
    bc.height = 125
    bc.width = 300
    bc.data = data

    bc.strokeColor = colors.black

    bc.valueAxis.valueMin = -30
    bc.valueAxis.valueMax = -10
    bc.valueAxis.valueStep = 15
    
    bc.categoryAxis.labels.boxAnchor = 'n'
    bc.categoryAxis.labels.dy = -5
    bc.categoryAxis.categoryNames = ['Ying', 'Yang']

    drawing.add(bc)

    return drawing    


###

##dataSample5 = [(10, 20), (20, 30), (30, 40), (40, 50), (50, 60)]
##dataSample5 = [(10, 60), (20, 50), (30, 40), (40, 30), (50, 20)]
dataSample5 = [(10, 60), (20, 50), (30, 40), (40, 30)]

def sampleV5a():
    "A simple bar chart with no expressed spacing attributes."
    
    drawing = Drawing(400, 200)

    data = dataSample5
    
    bc = VerticalBarChart()
    bc.x = 50
    bc.y = 50
    bc.height = 125
    bc.width = 300
    bc.data = data
    bc.strokeColor = colors.black

    bc.valueAxis.valueMin = 0
    bc.valueAxis.valueMax = 60
    bc.valueAxis.valueStep = 15
    
    bc.categoryAxis.labels.boxAnchor = 'n'
    bc.categoryAxis.labels.dy = -5
    bc.categoryAxis.categoryNames = ['Ying', 'Yang']

    drawing.add(bc)

    return drawing

    
def sampleV5b():
    "A simple bar chart with proportional spacing."
    
    drawing = Drawing(400, 200)

    data = dataSample5
    
    bc = VerticalBarChart()
    bc.x = 50
    bc.y = 50
    bc.height = 125
    bc.width = 300
    bc.data = data
    bc.strokeColor = colors.black

    bc.useAbsolute = 0
    bc.barWidth = 40
    bc.groupSpacing = 20
    bc.barSpacing = 10

    bc.valueAxis.valueMin = 0
    bc.valueAxis.valueMax = 60
    bc.valueAxis.valueStep = 15
    
    bc.categoryAxis.labels.boxAnchor = 'n'
    bc.categoryAxis.labels.dy = -5
    bc.categoryAxis.categoryNames = ['Ying', 'Yang']

    drawing.add(bc)

    return drawing

    
def sampleV5c1():
    "Make sampe simple bar chart but with absolute spacing."
    
    drawing = Drawing(400, 200)

    data = dataSample5
    
    bc = VerticalBarChart()
    bc.x = 50
    bc.y = 50
    bc.height = 125
    bc.width = 300
    bc.data = data
    bc.strokeColor = colors.black

    bc.useAbsolute = 1
    bc.barWidth = 40
    bc.groupSpacing = 0
    bc.barSpacing = 0

    bc.valueAxis.valueMin = 0
    bc.valueAxis.valueMax = 60
    bc.valueAxis.valueStep = 15
    
    bc.categoryAxis.labels.boxAnchor = 'n'
    bc.categoryAxis.labels.dy = -5
    bc.categoryAxis.categoryNames = ['Ying', 'Yang']

    drawing.add(bc)

    return drawing    


def sampleV5c2():
    "Make sampe simple bar chart but with absolute spacing."
    
    drawing = Drawing(400, 200)

    data = dataSample5
    
    bc = VerticalBarChart()
    bc.x = 50
    bc.y = 50
    bc.height = 125
    bc.width = 300
    bc.data = data
    bc.strokeColor = colors.black

    bc.useAbsolute = 1
    bc.barWidth = 40
    bc.groupSpacing = 20
    bc.barSpacing = 0

    bc.valueAxis.valueMin = 0
    bc.valueAxis.valueMax = 60
    bc.valueAxis.valueStep = 15
    
    bc.categoryAxis.labels.boxAnchor = 'n'
    bc.categoryAxis.labels.dy = -5
    bc.categoryAxis.categoryNames = ['Ying', 'Yang']

    drawing.add(bc)

    return drawing    


def sampleV5c3():
    "Make sampe simple bar chart but with absolute spacing."
    
    drawing = Drawing(400, 200)

    data = dataSample5
    
    bc = VerticalBarChart()
    bc.x = 50
    bc.y = 50
    bc.height = 125
    bc.width = 300
    bc.data = data
    bc.strokeColor = colors.black

    bc.useAbsolute = 1
    bc.barWidth = 40
    bc.groupSpacing = 0
    bc.barSpacing = 10

    bc.valueAxis.valueMin = 0
    bc.valueAxis.valueMax = 60
    bc.valueAxis.valueStep = 15
    
    bc.categoryAxis.labels.boxAnchor = 'n'
    bc.categoryAxis.labels.dy = -5
    bc.categoryAxis.categoryNames = ['Ying', 'Yang']

    drawing.add(bc)

    return drawing    


def sampleV5c4():
    "Make sampe simple bar chart but with absolute spacing."
    
    drawing = Drawing(400, 200)

    data = dataSample5
    
    bc = VerticalBarChart()
    bc.x = 50
    bc.y = 50
    bc.height = 125
    bc.width = 300
    bc.data = data
    bc.strokeColor = colors.black

    bc.useAbsolute = 1
    bc.barWidth = 40
    bc.groupSpacing = 20
    bc.barSpacing = 10

    bc.valueAxis.valueMin = 0
    bc.valueAxis.valueMax = 60
    bc.valueAxis.valueStep = 15
    
    bc.categoryAxis.labels.boxAnchor = 'n'
    bc.categoryAxis.labels.dy = -5
    bc.categoryAxis.categoryNames = ['Ying', 'Yang']

    drawing.add(bc)

    return drawing    


# Horizontal samples

def sampleH0a():
    "Make a slightly pathologic bar chart with only TWO data items."
    
    drawing = Drawing(400, 200)

    data = [(13, 20)]
    
    bc = HorizontalBarChart()
    bc.x = 50
    bc.y = 50
    bc.height = 125
    bc.width = 300
    bc.data = data

    bc.strokeColor = colors.black

    bc.valueAxis.valueMin = 0
    bc.valueAxis.valueMax = 60
    bc.valueAxis.valueStep = 15
    
    bc.categoryAxis.labels.boxAnchor = 'se'
    bc.categoryAxis.labels.angle = 30
    bc.categoryAxis.categoryNames = ['Ying', 'Yang']

    drawing.add(bc)

    return drawing    

    
def sampleH0b():
    "Make a pathologic bar chart with only ONE data item."
    
    drawing = Drawing(400, 200)

    data = [(42,)]
    
    bc = HorizontalBarChart()
    bc.x = 50
    bc.y = 50
    bc.height = 125
    bc.width = 300
    bc.data = data
    bc.strokeColor = colors.black

    bc.valueAxis.valueMin = 0
    bc.valueAxis.valueMax = 50
    bc.valueAxis.valueStep = 15
    
    bc.categoryAxis.labels.boxAnchor = 'se'
    bc.categoryAxis.labels.angle = 30
    bc.categoryAxis.categoryNames = ['Jan-99']

    drawing.add(bc)

    return drawing    

    
def sampleH0c():
    "Make a really pathologic bar chart with NO data items at all!"
    
    drawing = Drawing(400, 200)

    data = [()]
    
    bc = HorizontalBarChart()
    bc.x = 50
    bc.y = 50
    bc.height = 125
    bc.width = 300
    bc.data = data
    bc.strokeColor = colors.black

    bc.valueAxis.valueMin = 0
    bc.valueAxis.valueMax = 60
    bc.valueAxis.valueStep = 15
    
    bc.categoryAxis.labels.boxAnchor = 'se'
    bc.categoryAxis.labels.angle = 30
    bc.categoryAxis.categoryNames = []

    drawing.add(bc)

    return drawing    

    
def sampleH1():
    "Sample of multi-series bar chart."

    drawing = Drawing(400, 200)

    data = [
            (13, 5, 20, 22, 37, 45, 19, 4),
            (14, 6, 21, 23, 38, 46, 20, 5)
            ]
    
    bc = HorizontalBarChart()
    bc.x = 50
    bc.y = 50
    bc.height = 125
    bc.width = 300
    bc.data = data
    bc.strokeColor = colors.black

    bc.valueAxis.valueMin = 0
    bc.valueAxis.valueMax = 60
    bc.valueAxis.valueStep = 15
    
    bc.categoryAxis.labels.boxAnchor = 'e'
    catNames = string.split('Jan Feb Mar Apr May Jun Jul Aug', ' ')
    catNames = map(lambda n:n+'-99', catNames)
    bc.categoryAxis.categoryNames = catNames
    drawing.add(bc)

    return drawing    


def sampleH2a():
    "Sample of multi-series bar chart."
    
    data = [(2.4, -5.7, 2, 5, 9.2),
            (0.6, -4.9, -3, 4, 6.8)
            ]

    labels = ("Q3 2000", "Year to Date", "12 months",
              "Annualised\n3 years", "Since 07.10.99")

    drawing = Drawing(400, 200)

    bc = HorizontalBarChart()
    bc.x = 80
    bc.y = 50
    bc.height = 120
    bc.width = 300
    bc.data = data

    bc.barSpacing = 0
    bc.groupSpacing = 10
    bc.barWidth = 10
    
    bc.valueAxis.valueMin = -15
    bc.valueAxis.valueMax = +15
    bc.valueAxis.valueStep = 5
    bc.valueAxis.labels.fontName = 'Helvetica'
    bc.valueAxis.labels.fontSize = 8    
    bc.valueAxis.labels.boxAnchor = 'n'   # irrelevant (becomes 'c')
    bc.valueAxis.labels.textAnchor = 'middle'
    bc.valueAxis.configure(bc.data)

    bc.categoryAxis.categoryNames = labels
    bc.categoryAxis.labels.fontName = 'Helvetica'
    bc.categoryAxis.labels.fontSize = 8
    bc.categoryAxis.labels.dx = -150
    
    drawing.add(bc)

    return drawing


def sampleH2b():
    "Sample of multi-series bar chart."

    data = [(2.4, -5.7, 2, 5, 9.2),
            (0.6, -4.9, -3, 4, 6.8)
            ]

    labels = ("Q3 2000", "Year to Date", "12 months",
              "Annualised\n3 years", "Since 07.10.99")

    drawing = Drawing(400, 200)

    bc = HorizontalBarChart()
    bc.x = 80
    bc.y = 50
    bc.height = 120
    bc.width = 300
    bc.data = data

    bc.barSpacing = 5
    bc.groupSpacing = 10
    bc.barWidth = 10
    
    bc.valueAxis.valueMin = -15
    bc.valueAxis.valueMax = +15
    bc.valueAxis.valueStep = 5
    bc.valueAxis.labels.fontName = 'Helvetica'
    bc.valueAxis.labels.fontSize = 8    
    bc.valueAxis.labels.boxAnchor = 'n'   # irrelevant (becomes 'c')
    bc.valueAxis.labels.textAnchor = 'middle'

    bc.categoryAxis.categoryNames = labels
    bc.categoryAxis.labels.fontName = 'Helvetica'
    bc.categoryAxis.labels.fontSize = 8
    bc.categoryAxis.labels.dx = -150
    
    drawing.add(bc)    

    return drawing


def sampleH2c():
    "Sample of multi-series bar chart."

    data = [(2.4, -5.7, 2, 5, 9.99),
            (0.6, -4.9, -3, 4, 9.99)
            ]

    labels = ("Q3 2000", "Year to Date", "12 months",
              "Annualised\n3 years", "Since 07.10.99")

    drawing = Drawing(400, 200)

    bc = HorizontalBarChart()
    bc.x = 80
    bc.y = 50
    bc.height = 120
    bc.width = 300
    bc.data = data

    bc.barSpacing = 2
    bc.groupSpacing = 10
    bc.barWidth = 10
    
    bc.valueAxis.valueMin = -15
    bc.valueAxis.valueMax = +15
    bc.valueAxis.valueStep = 5
    bc.valueAxis.labels.fontName = 'Helvetica'
    bc.valueAxis.labels.fontSize = 8    
    bc.valueAxis.labels.boxAnchor = 'n'
    bc.valueAxis.labels.textAnchor = 'middle'

    bc.categoryAxis.categoryNames = labels
    bc.categoryAxis.labels.fontName = 'Helvetica'
    bc.categoryAxis.labels.fontSize = 8
    bc.categoryAxis.labels.dx = -150

    bc.barLabelNudge = 10
    
    bc.barLabelFormat = '%0.2f'
    bc.barLabels.dx = 0
    bc.barLabels.dy = 0
    bc.barLabels.boxAnchor = 'n'  # irrelevant (becomes 'c')
    bc.barLabels.fontName = 'Helvetica'
    bc.barLabels.fontSize = 6

    drawing.add(bc)    

    return drawing


def sampleH3():
    "A really horizontal bar chart (compared to the equivalent faked one)."

    names = ("UK Equities", "US Equities", "European Equities", "Japanese Equities",
              "Pacific (ex Japan) Equities", "Emerging Markets Equities",
              "UK Bonds", "Overseas Bonds", "UK Index-Linked", "Cash")

    series1 = (-1.5, 0.3, 0.5, 1.0, 0.8, 0.7, 0.4, 0.1, 1.0, 0.3)    
    series2 = (0.0, 0.33, 0.55, 1.1, 0.88, 0.77, 0.44, 0.11, 1.10, 0.33)

    assert len(names) == len(series1), "bad data"
    assert len(names) == len(series2), "bad data"
    
    drawing = Drawing(400, 200)

    bc = HorizontalBarChart()
    bc.x = 100
    bc.y = 20
    bc.height = 150
    bc.width = 250
    bc.data = (series1,)
    bc.defaultColors = (colors.green,)

    bc.barLabelFormat = '%0.2f'
    bc.barLabels.dx = 0
    bc.barLabels.dy = 0
    bc.barLabels.boxAnchor = 'w' # irrelevant (becomes 'c')
    bc.barLabels.fontName = 'Helvetica'
    bc.barLabels.fontSize = 6
    bc.barLabelNudge = 10
    
    bc.valueAxis.visible = 0
    bc.valueAxis.valueMin = -2
    bc.valueAxis.valueMax = +2
    bc.valueAxis.valueStep = 1

    bc.categoryAxis.tickLeft = 0
    bc.categoryAxis.tickRight = 0
    bc.categoryAxis.categoryNames = names
    bc.categoryAxis.labels.boxAnchor = 'w'
    bc.categoryAxis.labels.dx = -170
    bc.categoryAxis.labels.fontName = 'Helvetica'
    bc.categoryAxis.labels.fontSize = 6
        
    g = Group(bc)    
    drawing.add(g)    

    return drawing


def sampleH4a():
    "A bar chart showing value axis region starting at *exactly* zero."
    
    drawing = Drawing(400, 200)

    data = [(13, 20)]
    
    bc = HorizontalBarChart()
    bc.x = 50
    bc.y = 50
    bc.height = 125
    bc.width = 300
    bc.data = data

    bc.strokeColor = colors.black

    bc.valueAxis.valueMin = 0
    bc.valueAxis.valueMax = 60
    bc.valueAxis.valueStep = 15
    
    bc.categoryAxis.labels.boxAnchor = 'e'
    bc.categoryAxis.categoryNames = ['Ying', 'Yang']

    drawing.add(bc)

    return drawing    

    
def sampleH4b():
    "A bar chart showing value axis region starting *below* zero."
    
    drawing = Drawing(400, 200)

    data = [(13, 20)]
    
    bc = HorizontalBarChart()
    bc.x = 50
    bc.y = 50
    bc.height = 125
    bc.width = 300
    bc.data = data

    bc.strokeColor = colors.black

    bc.valueAxis.valueMin = -10
    bc.valueAxis.valueMax = 60
    bc.valueAxis.valueStep = 15
    
    bc.categoryAxis.labels.boxAnchor = 'e'
    bc.categoryAxis.categoryNames = ['Ying', 'Yang']

    drawing.add(bc)

    return drawing    

    
def sampleH4c():
    "A bar chart showing value axis region starting *above* zero."
    
    drawing = Drawing(400, 200)

    data = [(13, 20)]

    bc = HorizontalBarChart()
    bc.x = 50
    bc.y = 50
    bc.height = 125
    bc.width = 300
    bc.data = data

    bc.strokeColor = colors.black

    bc.valueAxis.valueMin = 10
    bc.valueAxis.valueMax = 60
    bc.valueAxis.valueStep = 15
    
    bc.categoryAxis.labels.boxAnchor = 'e'
    bc.categoryAxis.categoryNames = ['Ying', 'Yang']

    drawing.add(bc)

    return drawing    


def sampleH4d():
    "A bar chart showing value axis region entirely *below* zero."
    
    drawing = Drawing(400, 200)

    data = [(-13, -20)]

    bc = HorizontalBarChart()
    bc.x = 50
    bc.y = 50
    bc.height = 125
    bc.width = 300
    bc.data = data

    bc.strokeColor = colors.black

    bc.valueAxis.valueMin = -30
    bc.valueAxis.valueMax = -10
    bc.valueAxis.valueStep = 15
    
    bc.categoryAxis.labels.boxAnchor = 'e'
    bc.categoryAxis.categoryNames = ['Ying', 'Yang']

    drawing.add(bc)

    return drawing    


dataSample5 = [(10, 60), (20, 50), (30, 40), (40, 30)]

def sampleH5a():
    "A simple bar chart with no expressed spacing attributes."
    
    drawing = Drawing(400, 200)

    data = dataSample5
    
    bc = HorizontalBarChart()
    bc.x = 50
    bc.y = 50
    bc.height = 125
    bc.width = 300
    bc.data = data
    bc.strokeColor = colors.black

    bc.valueAxis.valueMin = 0
    bc.valueAxis.valueMax = 60
    bc.valueAxis.valueStep = 15
    
    bc.categoryAxis.labels.boxAnchor = 'e'
    bc.categoryAxis.categoryNames = ['Ying', 'Yang']

    drawing.add(bc)

    return drawing

    
def sampleH5b():
    "A simple bar chart with proportional spacing."
    
    drawing = Drawing(400, 200)

    data = dataSample5
    
    bc = HorizontalBarChart()
    bc.x = 50
    bc.y = 50
    bc.height = 125
    bc.width = 300
    bc.data = data
    bc.strokeColor = colors.black

    bc.useAbsolute = 0
    bc.barWidth = 40
    bc.groupSpacing = 20
    bc.barSpacing = 10

    bc.valueAxis.valueMin = 0
    bc.valueAxis.valueMax = 60
    bc.valueAxis.valueStep = 15
    
    bc.categoryAxis.labels.boxAnchor = 'e'
    bc.categoryAxis.categoryNames = ['Ying', 'Yang']

    drawing.add(bc)

    return drawing

    
def sampleH5c1():
    "A simple bar chart with absolute spacing."
    
    drawing = Drawing(400, 200)

    data = dataSample5
    
    bc = HorizontalBarChart()
    bc.x = 50
    bc.y = 50
    bc.height = 125
    bc.width = 300
    bc.data = data
    bc.strokeColor = colors.black

    bc.useAbsolute = 1
    bc.barWidth = 10
    bc.groupSpacing = 0
    bc.barSpacing = 0

    bc.valueAxis.valueMin = 0
    bc.valueAxis.valueMax = 60
    bc.valueAxis.valueStep = 15
    
    bc.categoryAxis.labels.boxAnchor = 'e'
    bc.categoryAxis.categoryNames = ['Ying', 'Yang']

    drawing.add(bc)

    return drawing    


def sampleH5c2():
    "Simple bar chart with absolute spacing."
    
    drawing = Drawing(400, 200)

    data = dataSample5
    
    bc = HorizontalBarChart()
    bc.x = 50
    bc.y = 50
    bc.height = 125
    bc.width = 300
    bc.data = data
    bc.strokeColor = colors.black

    bc.useAbsolute = 1
    bc.barWidth = 10
    bc.groupSpacing = 20
    bc.barSpacing = 0

    bc.valueAxis.valueMin = 0
    bc.valueAxis.valueMax = 60
    bc.valueAxis.valueStep = 15
    
    bc.categoryAxis.labels.boxAnchor = 'e'
    bc.categoryAxis.categoryNames = ['Ying', 'Yang']

    drawing.add(bc)

    return drawing    


def sampleH5c3():
    "Simple bar chart with absolute spacing."
    
    drawing = Drawing(400, 200)

    data = dataSample5
    
    bc = HorizontalBarChart()
    bc.x = 50
    bc.y = 50
    bc.height = 125
    bc.width = 300
    bc.data = data
    bc.strokeColor = colors.black

    bc.useAbsolute = 1
    bc.barWidth = 10
    bc.groupSpacing = 0
    bc.barSpacing = 10

    bc.valueAxis.valueMin = 0
    bc.valueAxis.valueMax = 60
    bc.valueAxis.valueStep = 15
    
    bc.categoryAxis.labels.boxAnchor = 'e'
    bc.categoryAxis.categoryNames = ['Ying', 'Yang']

    drawing.add(bc)

    return drawing    


def sampleH5c4():
    "Simple bar chart with absolute spacing."
    
    drawing = Drawing(400, 200)

    data = dataSample5
    
    bc = HorizontalBarChart()
    bc.x = 50
    bc.y = 50
    bc.height = 125
    bc.width = 300
    bc.data = data
    bc.strokeColor = colors.black

    bc.useAbsolute = 1
    bc.barWidth = 10
    bc.groupSpacing = 20
    bc.barSpacing = 10

    bc.valueAxis.valueMin = 0
    bc.valueAxis.valueMax = 60
    bc.valueAxis.valueStep = 15
    
    bc.categoryAxis.labels.boxAnchor = 'e'
    bc.categoryAxis.categoryNames = ['Ying', 'Yang']

    drawing.add(bc)

    return drawing    