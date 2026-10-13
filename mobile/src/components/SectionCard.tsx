import {
  StyleSheet,
  Text,
  View,
} from "react-native";

import { Colors } from "../constants/colors";

interface Props {
  title: string;
  children: React.ReactNode;
}

export default function SectionCard({
  title,
  children,
}: Props) {
  return (
    <View style={styles.card}>
      <Text style={styles.title}>
        {title}
      </Text>

      {children}
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: Colors.white,
    borderRadius: 18,
    padding: 18,
    marginBottom: 14,
    borderWidth: 1,
    borderColor: Colors.border,
  },

  title: {
    fontSize: 17,
    fontWeight: "700",
    color: Colors.primary,
    marginBottom: 14,
  },
});