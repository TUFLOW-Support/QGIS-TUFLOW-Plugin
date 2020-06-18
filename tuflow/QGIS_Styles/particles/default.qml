<!DOCTYPE qgis PUBLIC 'http://mrcc.com/qgis.dtd' 'SYSTEM'>
<qgis simplifyMaxScale="1" hasScaleBasedVisibilityFlag="0" labelsEnabled="0" simplifyDrawingTol="1" styleCategories="AllStyleCategories" readOnly="0" simplifyLocal="1" simplifyDrawingHints="0" version="3.13.0-Master" simplifyAlgorithm="0" minScale="100000000" maxScale="0">
  <flags>
    <Identifiable>1</Identifiable>
    <Removable>1</Removable>
    <Searchable>1</Searchable>
  </flags>
  <renderer-v2 forceraster="0" type="singleSymbol" enableorderby="0" symbollevels="0">
    <symbols>
      <symbol type="marker" name="0" force_rhr="0" alpha="1" clip_to_extent="1">
        <layer enabled="1" class="SimpleMarker" pass="0" locked="0">
          <prop k="angle" v="0"/>
          <prop k="color" v="166,206,227,255"/>
          <prop k="horizontal_anchor_point" v="1"/>
          <prop k="joinstyle" v="bevel"/>
          <prop k="name" v="circle"/>
          <prop k="offset" v="0,0"/>
          <prop k="offset_map_unit_scale" v="3x:0,0,0,0,0,0"/>
          <prop k="offset_unit" v="MM"/>
          <prop k="outline_color" v="255,255,255,255"/>
          <prop k="outline_style" v="solid"/>
          <prop k="outline_width" v="0.2"/>
          <prop k="outline_width_map_unit_scale" v="3x:0,0,0,0,0,0"/>
          <prop k="outline_width_unit" v="MM"/>
          <prop k="scale_method" v="diameter"/>
          <prop k="size" v="2"/>
          <prop k="size_map_unit_scale" v="3x:0,0,0,0,0,0"/>
          <prop k="size_unit" v="MM"/>
          <prop k="vertical_anchor_point" v="1"/>
          <data_defined_properties>
            <Option type="Map">
              <Option type="QString" name="name" value=""/>
              <Option name="properties"/>
              <Option type="QString" name="type" value="collection"/>
            </Option>
          </data_defined_properties>
        </layer>
      </symbol>
    </symbols>
    <rotation/>
    <sizescale/>
  </renderer-v2>
  <customproperties>
    <property value="0" key="embeddedWidgets/count"/>
    <property key="variableNames"/>
    <property key="variableValues"/>
  </customproperties>
  <blendMode>0</blendMode>
  <featureBlendMode>0</featureBlendMode>
  <layerOpacity>1</layerOpacity>
  <SingleCategoryDiagramRenderer diagramType="Histogram" attributeLegend="1">
    <DiagramCategory spacing="5" maxScaleDenominator="1e+08" penWidth="0" spacingUnit="MM" sizeScale="3x:0,0,0,0,0,0" minScaleDenominator="0" lineSizeScale="3x:0,0,0,0,0,0" lineSizeType="MM" diagramOrientation="Up" penAlpha="255" penColor="#000000" sizeType="MM" opacity="1" backgroundAlpha="255" scaleBasedVisibility="0" width="15" labelPlacementMethod="XHeight" scaleDependency="Area" barWidth="5" minimumSize="0" rotationOffset="270" height="15" backgroundColor="#ffffff" enabled="0" spacingUnitScale="3x:0,0,0,0,0,0" direction="0" showAxis="1">
      <fontProperties style="Regular" description="Noto Sans,10,-1,0,50,0,0,0,0,0,Regular"/>
      <attribute label="" field="" color="#000000"/>
      <axisSymbol>
        <symbol type="line" name="" force_rhr="0" alpha="1" clip_to_extent="1">
          <layer enabled="1" class="SimpleLine" pass="0" locked="0">
            <prop k="capstyle" v="square"/>
            <prop k="customdash" v="5;2"/>
            <prop k="customdash_map_unit_scale" v="3x:0,0,0,0,0,0"/>
            <prop k="customdash_unit" v="MM"/>
            <prop k="draw_inside_polygon" v="0"/>
            <prop k="joinstyle" v="bevel"/>
            <prop k="line_color" v="35,35,35,255"/>
            <prop k="line_style" v="solid"/>
            <prop k="line_width" v="0.26"/>
            <prop k="line_width_unit" v="MM"/>
            <prop k="offset" v="0"/>
            <prop k="offset_map_unit_scale" v="3x:0,0,0,0,0,0"/>
            <prop k="offset_unit" v="MM"/>
            <prop k="ring_filter" v="0"/>
            <prop k="use_custom_dash" v="0"/>
            <prop k="width_map_unit_scale" v="3x:0,0,0,0,0,0"/>
            <data_defined_properties>
              <Option type="Map">
                <Option type="QString" name="name" value=""/>
                <Option name="properties"/>
                <Option type="QString" name="type" value="collection"/>
              </Option>
            </data_defined_properties>
          </layer>
        </symbol>
      </axisSymbol>
    </DiagramCategory>
  </SingleCategoryDiagramRenderer>
  <DiagramLayerSettings priority="0" placement="0" dist="0" zIndex="0" showAll="1" linePlacementFlags="18" obstacle="0">
    <properties>
      <Option type="Map">
        <Option type="QString" name="name" value=""/>
        <Option name="properties"/>
        <Option type="QString" name="type" value="collection"/>
      </Option>
    </properties>
  </DiagramLayerSettings>
  <geometryOptions geometryPrecision="0" removeDuplicateNodes="0">
    <activeChecks/>
    <checkConfiguration/>
  </geometryOptions>
  <referencedLayers/>
  <referencingLayers/>
  <fieldConfiguration>
    <field name="id">
      <editWidget type="Range">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
    <field name="stat">
      <editWidget type="Range">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
    <field name="groupID">
      <editWidget type="Range">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
    <field name="depth">
      <editWidget type="TextEdit">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
    <field name="age">
      <editWidget type="TextEdit">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
    <field name="mass">
      <editWidget type="TextEdit">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
    <field name="state_age">
      <editWidget type="TextEdit">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
    <field name="uvw_water_x">
      <editWidget type="TextEdit">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
    <field name="uvw_water_y">
      <editWidget type="TextEdit">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
    <field name="uvw_water_z">
      <editWidget type="TextEdit">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
    <field name="uvw_x">
      <editWidget type="TextEdit">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
    <field name="uvw_y">
      <editWidget type="TextEdit">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
    <field name="uvw_z">
      <editWidget type="TextEdit">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
    <field name="water_depth">
      <editWidget type="TextEdit">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
  </fieldConfiguration>
  <aliases>
    <alias name="" field="id" index="0"/>
    <alias name="" field="stat" index="1"/>
    <alias name="" field="groupID" index="2"/>
    <alias name="" field="depth" index="3"/>
    <alias name="" field="age" index="4"/>
    <alias name="" field="mass" index="5"/>
    <alias name="" field="state_age" index="6"/>
    <alias name="" field="uvw_water_x" index="7"/>
    <alias name="" field="uvw_water_y" index="8"/>
    <alias name="" field="uvw_water_z" index="9"/>
    <alias name="" field="uvw_x" index="10"/>
    <alias name="" field="uvw_y" index="11"/>
    <alias name="" field="uvw_z" index="12"/>
    <alias name="" field="water_depth" index="13"/>
  </aliases>
  <excludeAttributesWMS/>
  <excludeAttributesWFS/>
  <defaults>
    <default field="id" expression="" applyOnUpdate="0"/>
    <default field="stat" expression="" applyOnUpdate="0"/>
    <default field="groupID" expression="" applyOnUpdate="0"/>
    <default field="depth" expression="" applyOnUpdate="0"/>
    <default field="age" expression="" applyOnUpdate="0"/>
    <default field="mass" expression="" applyOnUpdate="0"/>
    <default field="state_age" expression="" applyOnUpdate="0"/>
    <default field="uvw_water_x" expression="" applyOnUpdate="0"/>
    <default field="uvw_water_y" expression="" applyOnUpdate="0"/>
    <default field="uvw_water_z" expression="" applyOnUpdate="0"/>
    <default field="uvw_x" expression="" applyOnUpdate="0"/>
    <default field="uvw_y" expression="" applyOnUpdate="0"/>
    <default field="uvw_z" expression="" applyOnUpdate="0"/>
    <default field="water_depth" expression="" applyOnUpdate="0"/>
  </defaults>
  <constraints>
    <constraint constraints="0" exp_strength="0" field="id" notnull_strength="0" unique_strength="0"/>
    <constraint constraints="0" exp_strength="0" field="stat" notnull_strength="0" unique_strength="0"/>
    <constraint constraints="0" exp_strength="0" field="groupID" notnull_strength="0" unique_strength="0"/>
    <constraint constraints="0" exp_strength="0" field="depth" notnull_strength="0" unique_strength="0"/>
    <constraint constraints="0" exp_strength="0" field="age" notnull_strength="0" unique_strength="0"/>
    <constraint constraints="0" exp_strength="0" field="mass" notnull_strength="0" unique_strength="0"/>
    <constraint constraints="0" exp_strength="0" field="state_age" notnull_strength="0" unique_strength="0"/>
    <constraint constraints="0" exp_strength="0" field="uvw_water_x" notnull_strength="0" unique_strength="0"/>
    <constraint constraints="0" exp_strength="0" field="uvw_water_y" notnull_strength="0" unique_strength="0"/>
    <constraint constraints="0" exp_strength="0" field="uvw_water_z" notnull_strength="0" unique_strength="0"/>
    <constraint constraints="0" exp_strength="0" field="uvw_x" notnull_strength="0" unique_strength="0"/>
    <constraint constraints="0" exp_strength="0" field="uvw_y" notnull_strength="0" unique_strength="0"/>
    <constraint constraints="0" exp_strength="0" field="uvw_z" notnull_strength="0" unique_strength="0"/>
    <constraint constraints="0" exp_strength="0" field="water_depth" notnull_strength="0" unique_strength="0"/>
  </constraints>
  <constraintExpressions>
    <constraint field="id" desc="" exp=""/>
    <constraint field="stat" desc="" exp=""/>
    <constraint field="groupID" desc="" exp=""/>
    <constraint field="depth" desc="" exp=""/>
    <constraint field="age" desc="" exp=""/>
    <constraint field="mass" desc="" exp=""/>
    <constraint field="state_age" desc="" exp=""/>
    <constraint field="uvw_water_x" desc="" exp=""/>
    <constraint field="uvw_water_y" desc="" exp=""/>
    <constraint field="uvw_water_z" desc="" exp=""/>
    <constraint field="uvw_x" desc="" exp=""/>
    <constraint field="uvw_y" desc="" exp=""/>
    <constraint field="uvw_z" desc="" exp=""/>
    <constraint field="water_depth" desc="" exp=""/>
  </constraintExpressions>
  <expressionfields/>
  <attributeactions>
    <defaultAction value="{00000000-0000-0000-0000-000000000000}" key="Canvas"/>
  </attributeactions>
  <attributetableconfig actionWidgetStyle="dropDown" sortExpression="" sortOrder="0">
    <columns>
      <column type="field" name="id" hidden="0" width="-1"/>
      <column type="field" name="stat" hidden="0" width="-1"/>
      <column type="field" name="groupID" hidden="0" width="-1"/>
      <column type="field" name="uvw_water_x" hidden="0" width="-1"/>
      <column type="field" name="uvw_water_y" hidden="0" width="-1"/>
      <column type="field" name="uvw_water_z" hidden="0" width="-1"/>
      <column type="field" name="uvw_x" hidden="0" width="-1"/>
      <column type="field" name="uvw_y" hidden="0" width="-1"/>
      <column type="field" name="uvw_z" hidden="0" width="-1"/>
      <column type="field" name="age" hidden="0" width="-1"/>
      <column type="field" name="mass" hidden="0" width="-1"/>
      <column type="field" name="depth" hidden="0" width="-1"/>
      <column type="field" name="state_age" hidden="0" width="-1"/>
      <column type="field" name="water_depth" hidden="0" width="-1"/>
      <column type="actions" hidden="1" width="-1"/>
    </columns>
  </attributetableconfig>
  <conditionalstyles>
    <rowstyles/>
    <fieldstyles/>
  </conditionalstyles>
  <storedexpressions/>
  <editform tolerant="1"></editform>
  <editforminit/>
  <editforminitcodesource>0</editforminitcodesource>
  <editforminitfilepath></editforminitfilepath>
  <editforminitcode><![CDATA[# -*- coding: utf-8 -*-
"""
QGIS forms can have a Python function that is called when the form is
opened.

Use this function to add extra logic to your forms.

Enter the name of the function in the "Python Init function"
field.
An example follows:
"""
from qgis.PyQt.QtWidgets import QWidget

def my_form_open(dialog, layer, feature):
	geom = feature.geometry()
	control = dialog.findChild(QWidget, "MyLineEdit")
]]></editforminitcode>
  <featformsuppress>0</featformsuppress>
  <editorlayout>generatedlayout</editorlayout>
  <editable>
    <field name="age" editable="1"/>
    <field name="depth" editable="1"/>
    <field name="diff_x" editable="1"/>
    <field name="diff_y" editable="1"/>
    <field name="diff_z" editable="1"/>
    <field name="groupID" editable="1"/>
    <field name="id" editable="1"/>
    <field name="mass" editable="1"/>
    <field name="stat" editable="1"/>
    <field name="state_age" editable="1"/>
    <field name="uvw_water_x" editable="1"/>
    <field name="uvw_water_y" editable="1"/>
    <field name="uvw_water_z" editable="1"/>
    <field name="uvw_x" editable="1"/>
    <field name="uvw_y" editable="1"/>
    <field name="uvw_z" editable="1"/>
    <field name="water_depth" editable="1"/>
  </editable>
  <labelOnTop>
    <field name="age" labelOnTop="0"/>
    <field name="depth" labelOnTop="0"/>
    <field name="diff_x" labelOnTop="0"/>
    <field name="diff_y" labelOnTop="0"/>
    <field name="diff_z" labelOnTop="0"/>
    <field name="groupID" labelOnTop="0"/>
    <field name="id" labelOnTop="0"/>
    <field name="mass" labelOnTop="0"/>
    <field name="stat" labelOnTop="0"/>
    <field name="state_age" labelOnTop="0"/>
    <field name="uvw_water_x" labelOnTop="0"/>
    <field name="uvw_water_y" labelOnTop="0"/>
    <field name="uvw_water_z" labelOnTop="0"/>
    <field name="uvw_x" labelOnTop="0"/>
    <field name="uvw_y" labelOnTop="0"/>
    <field name="uvw_z" labelOnTop="0"/>
    <field name="water_depth" labelOnTop="0"/>
  </labelOnTop>
  <dataDefinedFieldProperties/>
  <widgets/>
  <previewExpression>id</previewExpression>
  <mapTip></mapTip>
  <layerGeometryType>0</layerGeometryType>
</qgis>
