#!/bin/bash
set -e

# e-Gov XML XSD検証（例: data/RadioAct_ja.xml, data/law.xsd）
if [ -f data/law.xsd ]; then
  echo "[XSD] e-Gov XML XSD検証..."
  python3 -c "import xmlschema; xmlschema.XMLSchema('data/law.xsd').validate('data/RadioAct_ja.xml')" || { echo 'XSD検証失敗'; exit 1; }
else
  echo "[XSD] law.xsdが見つかりません。スキップします。"
fi

# JLT XML DTD検証（例: data/RadioAct_en.xml, data/jstatute.dtd）
if [ -f data/jstatute.dtd ]; then
  echo "[DTD] JLT XML DTD検証..."
  xmllint --noout --dtdvalid data/jstatute.dtd data/RadioAct_en.xml || { echo 'DTD検証失敗'; exit 1; }
else
  echo "[DTD] jstatute.dtdが見つかりません。スキップします。"
fi

echo "XMLバリデーション完了" 